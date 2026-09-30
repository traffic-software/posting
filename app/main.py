import hmac
from collections.abc import Callable
from contextlib import asynccontextmanager
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, status

from app.agent import run_task
from app.config import Settings
from app.schemas import TaskAccepted, TaskRequest, TaskResponse, TaskStatus
from app.storage import QueueFullError, TaskStore
from app.worker import TaskWorker


def create_app(settings: Settings | None = None, runner: Callable = run_task) -> FastAPI:
    settings = settings or Settings()
    store = TaskStore(settings.database_path)
    worker = TaskWorker(store, settings, runner=runner)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if settings.require_task_api_token and not settings.task_api_token:
            raise RuntimeError("TASK_API_TOKEN is required for public deployment")
        store.initialize()
        worker.start()
        try:
            yield
        finally:
            worker.stop()

    app = FastAPI(title="Browser Task API", lifespan=lifespan)
    app.state.store = store
    app.state.worker = worker

    def authorize(authorization: str | None = Header(default=None)) -> None:
        if not settings.task_api_token:
            return
        token = authorization.removeprefix("Bearer ") if authorization else ""
        if not hmac.compare_digest(token, settings.task_api_token):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    @app.post("/run-task", response_model=TaskAccepted, status_code=status.HTTP_202_ACCEPTED)
    def run(request: TaskRequest, _: None = Depends(authorize)) -> TaskAccepted:
        if not settings.host_allowlist or not all(
            (settings.openai_api_key, settings.openai_base_url, settings.model_name)
        ):
            raise HTTPException(status_code=503, detail="Task service is not configured")
        if not worker.alive:
            raise HTTPException(status_code=503, detail="Task worker is unavailable")
        try:
            task_id = store.create(request.prompt, settings.max_active_tasks)
        except QueueFullError as exc:
            raise HTTPException(status_code=429, detail="Task capacity reached") from exc
        worker.notify()
        return TaskAccepted(task_id=UUID(task_id), status=TaskStatus.PENDING)

    @app.get("/task-status/{task_id}", response_model=TaskResponse)
    def task_status(task_id: UUID, _: None = Depends(authorize)) -> TaskResponse:
        task = store.get(str(task_id))
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return TaskResponse(**task)

    @app.get("/health")
    def health():
        if not worker.alive or not store.healthy():
            raise HTTPException(status_code=503, detail="Task service unavailable")
        return {"status": "ok", "revision": settings.app_revision}

    @app.get("/ready")
    def ready():
        health()
        remote = urlsplit(settings.selenium_remote_url)
        if remote.scheme not in ("http", "https") or not remote.netloc:
            raise HTTPException(status_code=503, detail="Browser service unavailable")
        try:
            response = httpx.get(f"{remote.scheme}://{remote.netloc}/status", timeout=3)
            response.raise_for_status()
            if response.json().get("value", {}).get("ready") is not True:
                raise ValueError("Selenium is not ready")
        except (httpx.HTTPError, ValueError):
            raise HTTPException(status_code=503, detail="Browser service unavailable") from None
        return {"status": "ok", "revision": settings.app_revision}

    return app


app = create_app()
