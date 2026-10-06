import hmac
import logging
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from langchain_core.tools import ToolException

from app.agent import run_task
from app.browser_runtime import browser_ready
from app.config import Settings
from app.display_viewer import DisplayViewer, create_router
from app.schemas import TaskAccepted, TaskRequest, TaskResponse, TaskStatus
from app.storage import QueueFullError, TaskStore
from app.selenium_tools import check_url
from app.task_context import encode_context, encode_file_sources
from app.worker import TaskWorker
from app.browser_profiles import BrowserProfileStore, ProfileError
from app.browser_sessions import BrowserSessionManager
from app.artifacts import ArtifactAccessLogFilter, ArtifactError, ArtifactFileResponse, ArtifactManager


def create_app(settings: Settings | None = None, runner: Callable = run_task) -> FastAPI:
    settings = settings or Settings()
    viewer = DisplayViewer(settings)
    settings._display_viewer = viewer
    store = TaskStore(settings.database_path)
    settings._workflow_store = store
    artifacts = ArtifactManager(settings, store) if settings.enable_file_transfers else None
    settings._artifact_manager = artifacts
    if artifacts is not None:
        access_logger = logging.getLogger("uvicorn.access")
        if not any(isinstance(item, ArtifactAccessLogFilter) for item in access_logger.filters):
            access_logger.addFilter(ArtifactAccessLogFilter())
    profiles = BrowserProfileStore(settings.browser_profiles_root)
    sessions = BrowserSessionManager(settings, viewer, profiles)
    settings._browser_sessions = sessions
    worker = TaskWorker(store, settings, runner=runner)
    sessions.worker = worker

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if settings.require_task_api_token and not settings.task_api_token:
            raise RuntimeError("TASK_API_TOKEN is required for public deployment")
        store.initialize()
        try:
            if artifacts is not None:
                artifacts.initialize()
                artifacts.start()
            sessions.start()
            worker.start()
        except BaseException:
            if artifacts is not None:
                artifacts.close()
            raise
        try:
            yield
        finally:
            try:
                sessions.close()
            finally:
                try:
                    worker.stop()
                finally:
                    try:
                        viewer.close()
                    finally:
                        if artifacts is not None:
                            artifacts.close()

    app = FastAPI(title="Browser Task API", lifespan=lifespan)
    app.state.store = store
    app.state.artifacts = artifacts
    app.state.worker = worker
    app.state.viewer = viewer
    app.state.browser_sessions = sessions
    app.state.browser_profiles = profiles
    app.include_router(create_router(viewer, sessions, profiles, worker))

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
        file_task = bool(request.upload_sources or request.upload_origins or request.allow_file_downloads)
        if file_task and (artifacts is None or not settings.task_api_token):
            raise HTTPException(status_code=403, detail="File tasks require enabled file transfers and API authentication")
        if request.upload_sources and not settings.credential_fernet_key:
            raise HTTPException(status_code=503, detail="URL upload sources require a persistent CREDENTIAL_FERNET_KEY")
        if request.browser_profile_id:
            if not settings.task_api_token:
                raise HTTPException(status_code=403, detail="Persistent profile tasks require API authentication")
            try:
                profiles.get(request.browser_profile_id)
            except ProfileError as exc:
                raise HTTPException(status_code=422, detail="Invalid browser profile") from exc
        if request.credentials and not settings.task_api_token:
            raise HTTPException(status_code=403, detail="Credential tasks require API authentication")
        if request.allow_write_actions is True and not settings.enable_write_actions:
            raise HTTPException(status_code=403, detail="Write actions are disabled")
        try:
            from app.workflow_memory import safe_text
            from app.task_context import TaskContext
            criterion_context = TaskContext(credentials=list(request.credentials), upload_sources=list(request.upload_sources))
            for source in request.upload_sources:
                check_url(source.url.get_secret_value())
            for origin in request.upload_origins:
                check_url(origin)
            for criterion in request.workflow_success_criteria:
                check_url(criterion.origin)
                safe_text(criterion.expected_text, criterion_context, maximum=160)
                if criterion_context.redact(criterion.selector) != criterion.selector:
                    raise ValueError("Private outcome selector")
            for credential in request.credentials:
                for origin in credential.origins:
                    check_url(origin)
            if request.proxy:
                check_url(f"http://{request.proxy.endpoint}")
        except (ToolException, ValueError) as exc:
            raise HTTPException(status_code=422, detail="Invalid task destination or outcome criterion") from exc
        try:
            options, blob = encode_context(request, settings)
            sources_blob = encode_file_sources(request, settings)
        except (ValueError, UnicodeError) as exc:
            raise HTTPException(status_code=503, detail="Credential encryption is unavailable") from exc
        expires_at = (
            (datetime.now(timezone.utc) + timedelta(seconds=settings.credential_ttl_seconds)).isoformat()
            if blob else None
        )
        try:
            task_id = store.create(
                criterion_context.redact(request.prompt) if request.upload_sources else request.prompt,
                settings.max_active_tasks, context_json=options,
                credential_blob=blob, credential_expires_at=expires_at,
                file_sources_blob=sources_blob,
                file_sources_expires_at=(datetime.now(timezone.utc) + timedelta(seconds=settings.file_source_ttl_seconds)).isoformat() if sources_blob else None,
            )
        except QueueFullError as exc:
            raise HTTPException(status_code=429, detail="Task capacity reached") from exc
        worker.notify()
        return TaskAccepted(task_id=UUID(task_id), status=TaskStatus.PENDING)

    @app.get("/task-status/{task_id}", response_model=TaskResponse)
    def task_status(task_id: UUID, response: Response, _: None = Depends(authorize)) -> TaskResponse:
        task = store.get(str(task_id))
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        response.headers["Cache-Control"] = "no-store"
        return TaskResponse(**task, artifacts=artifacts.links(str(task_id)) if artifacts is not None else [])

    @app.api_route("/task-artifacts/{artifact_id}/download", methods=["GET", "HEAD"], include_in_schema=False)
    def download_artifact(artifact_id: str, expires: int = Query(ge=1), signature: str = Query(min_length=64, max_length=64, pattern=r"^[a-f0-9]{64}$")):
        if artifacts is None:
            raise HTTPException(status_code=404, detail="Download is unavailable")
        release = None
        try:
            path, row, release = artifacts.download_lease(artifact_id, expires, signature)
            return ArtifactFileResponse(path, row, release)
        except (ArtifactError, OSError):
            if release is not None:
                release()
            raise HTTPException(status_code=404, detail="Download is unavailable or expired") from None

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
