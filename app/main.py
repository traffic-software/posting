import hmac
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from langchain_core.tools import ToolException

from app.agent import run_task
from app.browser_runtime import browser_ready
from app.config import Settings
from app.schemas import TaskAccepted, TaskRequest, TaskResponse, TaskStatus
from app.storage import QueueFullError, TaskStore
from app.selenium_tools import check_url
from app.task_context import encode_context
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

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_request, _exc):
        return JSONResponse(status_code=422, content={"detail": "Invalid task request"})

    def authorize(authorization: str | None = Header(default=None)) -> None:
        if not settings.task_api_token:
            return
        token = authorization.removeprefix("Bearer ") if authorization else ""
        if not hmac.compare_digest(token, settings.task_api_token):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    @app.post("/run-task", response_model=TaskAccepted, status_code=status.HTTP_202_ACCEPTED)
    def run(request: TaskRequest, _: None = Depends(authorize)) -> TaskAccepted:
        if not all((settings.openai_api_key, settings.openai_base_url, settings.model_name)):
            raise HTTPException(status_code=503, detail="Task service is not configured")
        if not worker.alive:
            raise HTTPException(status_code=503, detail="Task worker is unavailable")
        if request.credentials and not settings.task_api_token:
            raise HTTPException(status_code=403, detail="Credential tasks require API authentication")
        if request.allow_write_actions is True and not settings.enable_write_actions:
            raise HTTPException(status_code=403, detail="Write actions are disabled")
        try:
            for credential in request.credentials:
                for origin in credential.origins:
                    check_url(origin)
            if request.proxy:
                check_url(f"http://{request.proxy.endpoint}")
        except ToolException as exc:
            raise HTTPException(status_code=422, detail="Invalid task destination") from exc
        try:
            options, blob = encode_context(request, settings)
        except (ValueError, UnicodeError) as exc:
            raise HTTPException(status_code=503, detail="Credential encryption is unavailable") from exc
        expires_at = (
            (datetime.now(timezone.utc) + timedelta(seconds=settings.credential_ttl_seconds)).isoformat()
            if blob else None
        )
        try:
            task_id = store.create(
                request.prompt, settings.max_active_tasks, context_json=options,
                credential_blob=blob, credential_expires_at=expires_at,
            )
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
        if not browser_ready(settings):
            raise HTTPException(status_code=503, detail="Browser service unavailable")
        return {"status": "ok", "revision": settings.app_revision}

    return app


app = create_app()
