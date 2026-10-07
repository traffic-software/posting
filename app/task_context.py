import json
import time
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from contextlib import contextmanager

from cryptography.fernet import Fernet

from app.config import Settings
from app.schemas import FixedProxy, LoginCredential, TaskRequest, UploadSource, WorkflowSuccessCriterion


class TaskControlError(RuntimeError):
    pass


class TaskDeadlineExceeded(TimeoutError):
    pass


class ExecutionBudget:
    """A shared, moving monotonic deadline; only acknowledged manual time is free."""
    def __init__(self, seconds: float):
        self._lock = threading.Lock()
        self._deadline = time.monotonic() + seconds
        self._frozen = None

    @property
    def deadline(self):
        with self._lock:
            return self._deadline + (time.monotonic() - self._frozen if self._frozen is not None else 0)

    def freeze(self):
        with self._lock:
            if self._frozen is None:
                self._frozen = time.monotonic()

    def resume(self):
        with self._lock:
            if self._frozen is not None:
                self._deadline += time.monotonic() - self._frozen
                self._frozen = None

    def __rsub__(self, value):
        return value - self.deadline

    def __sub__(self, value):
        return self.deadline - value

    def __le__(self, value):
        return self.deadline <= value

    def __lt__(self, value):
        return self.deadline < value

    def __ge__(self, value):
        return self.deadline >= value

    def __gt__(self, value):
        return self.deadline > value


class TaskControl:
    """Gate complete tools/model calls, never individual click/type checkpoints."""
    def __init__(self):
        self.condition = threading.Condition(threading.RLock())
        self.state = "agent"
        self.owner = None
        self.expires_at = None
        self.active = 0
        self.local = threading.local()
        self.epoch = 0
        self.transition = None
        self.observe = None
        self.budget = None

    @contextmanager
    def action(self, context):
        nested = getattr(self.local, "depth", 0) > 0
        with self.condition:
            if not nested:
                while self.state != "agent":
                    context.check_alive()
                    self.condition.wait(0.1)
                context.check_alive()
                self.active += 1
            self.local.depth = getattr(self.local, "depth", 0) + 1
        try:
            yield
        finally:
            with self.condition:
                self.local.depth -= 1
                if not nested:
                    self.active -= 1
                self.condition.notify_all()

    def wake(self):
        with self.condition:
            self.condition.notify_all()


@dataclass(repr=False)
class TaskContext:
    allow_write_actions: bool | None = None
    proxy: FixedProxy | None = None
    browser_profile_id: str | None = None
    task_id: str | None = None
    allow_file_downloads: bool = False
    upload_sources: list[UploadSource] = field(default_factory=list)
    upload_origins: list[str] = field(default_factory=list)
    file_sources_expires_at: float | None = None
    _artifact_session: object | None = field(default=None, init=False)
    _browser_downloads: object | None = field(default=None, init=False)
    workflow_success_criteria: list[WorkflowSuccessCriterion] = field(default_factory=list)
    _workflow_candidate: dict | None = field(default=None, init=False)
    _workflow_evidence: list[dict] = field(default_factory=list, init=False)
    _workflow_lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    _workflow_verifier: Callable | None = field(default=None, init=False)
    _workflow_terminal_verified: bool = field(default=False, init=False)
    control: TaskControl = field(default_factory=TaskControl)
    credentials: list[LoginCredential] = field(default_factory=list)
    credential_expires_at: float | None = None
    cancelled: threading.Event = field(default_factory=threading.Event)
    _browser_lock: threading.Lock = field(default_factory=threading.Lock)
    _browser_close: Callable | None = None
    _totp_codes: set[str] = field(default_factory=set)
    _totp_attempts: dict[str, set[int]] = field(default_factory=dict)
    _secret_lock: threading.Lock = field(default_factory=threading.Lock)
    _observations: list[dict] = field(default_factory=list)
    _observation_lock: threading.Lock = field(default_factory=threading.Lock)
    execution_phase: str = field(default="execution", init=False)
    _failure_origin: tuple | None = field(default=None, init=False, repr=False)

    def record_failure(self, exc: Exception, phase: str, tool: str | None = None, code: str | None = None) -> None:
        with self._observation_lock:
            # Preserve the innermost boundary for this exact exception, not a past refusal.
            if self._failure_origin is None or self._failure_origin[0] is not exc:
                self._failure_origin = (exc, phase, tool, code)

    def failure_origin(self, exc: Exception, fallback: str) -> tuple:
        with self._observation_lock:
            if self._failure_origin is not None and self._failure_origin[0] is exc:
                return self._failure_origin[1:]
        return fallback, None, None

    def check_alive(self) -> None:
        if self.cancelled.is_set():
            raise TaskControlError("Task cancelled")
        if self.credential_expires_at is not None and time.time() >= self.credential_expires_at:
            raise TaskControlError("Task credentials expired")
        if self.control.budget is not None and time.monotonic() >= self.control.budget:
            raise TaskDeadlineExceeded("Task time limit reached")

    def bind_browser(self, close: Callable) -> None:
        with self._browser_lock:
            if not self.cancelled.is_set():
                self._browser_close = close
                return
        close()
        raise RuntimeError("Task cancelled")

    def close_browser(self) -> None:
        with self._browser_lock:
            close, self._browser_close = self._browser_close, None
        if close is not None:
            close()

    def cancel(self) -> None:
        self.cancelled.set()
        self.control.wake()
        try:
            self.close_browser()
        finally:
            self.clear_sensitive_state()

    def record_observation(self, tool: str, outcome: str, detail: str, *, code: str | None = None) -> None:
        entry = {"tool": tool, "outcome": outcome, "detail": self.redact(detail)[:500]}
        if code is not None:
            entry["code"] = code
        with self._observation_lock:
            if not self.cancelled.is_set():
                self._observations.append(entry)
                del self._observations[:-12]

    def observations(self) -> list[dict]:
        with self._observation_lock:
            entries = [dict(entry) for entry in self._observations]
        return self.redacted_result({"events": entries})["events"]

    def stage_workflow(self, candidate: dict) -> None:
        from copy import deepcopy
        with self._workflow_lock:
            self._workflow_candidate = deepcopy(candidate)
            self._workflow_evidence.clear()
            self._workflow_terminal_verified = False

    def record_workflow_evidence(self, evidence: list[dict]) -> None:
        from copy import deepcopy
        with self._workflow_lock:
            self._workflow_evidence = deepcopy(evidence) if not self.cancelled.is_set() else []
            self._workflow_terminal_verified = False

    def workflow_state(self) -> tuple[dict | None, list[dict]]:
        from copy import deepcopy
        with self._workflow_lock:
            return deepcopy(self._workflow_candidate), deepcopy(self._workflow_evidence)

    def clear_sensitive_state(self) -> None:
        downloads, self._browser_downloads = self._browser_downloads, None
        if downloads is not None:
            try:
                downloads.close()
            except Exception:
                pass
        artifacts, self._artifact_session = self._artifact_session, None
        if artifacts is not None:
            try:
                artifacts.close()
            except Exception:
                pass
        visual = getattr(self, "_visual_targets", None)
        if visual:
            visual.invalidate()
        self._vision_payload = None
        with self._workflow_lock:
            self._workflow_candidate = None
            self._workflow_evidence.clear()
            self._workflow_verifier = None
            self._workflow_terminal_verified = False
            self.workflow_success_criteria.clear()
        with self._observation_lock:
            self._observations.clear()
            self._failure_origin = None
        with self._secret_lock:
            self.credentials.clear()
            self.upload_sources.clear()
            self.upload_origins.clear()
            self._totp_codes.clear()
            self._totp_attempts.clear()

    def reserve_totp(self, credential: LoginCredential, timestep: int, code: str) -> None:
        with self._secret_lock:
            if self.cancelled.is_set() or not any(item is credential for item in self.credentials):
                raise RuntimeError("Task credentials unavailable")
            attempts = self._totp_attempts.setdefault(credential.id, set())
            if timestep in attempts or len(attempts) >= 2:
                raise RuntimeError("Authenticator attempt limit reached")
            attempts.add(timestep)
            self._totp_codes.add(code)

    def redact(self, text: str) -> str:
        import re
        text = re.sub(r"data:image/[^;\s]+;base64,[A-Za-z0-9+/=]+", "[IMAGE OMITTED]", text)
        image_payload = getattr(self, "_vision_payload", None)
        if image_payload:
            text = text.replace(image_payload, "[IMAGE OMITTED]")
        with self._secret_lock:
            secrets = self._totp_codes | {
                secret.get_secret_value()
                for credential in self.credentials
                for secret in (credential.username, credential.password, credential.totp_secret)
                if secret is not None
            }
            from urllib.parse import quote, quote_plus, unquote_plus, urlsplit
            for source in self.upload_sources:
                url = source.url.get_secret_value()
                secrets.add(url)
                query = urlsplit(url).query
                for item in query.split("&"):
                    raw_key, separator, raw_value = item.partition("=")
                    key, value = unquote_plus(raw_key).lower(), unquote_plus(raw_value)
                    if separator and len(value) >= 4 and (key in {"signature", "sig", "token", "key", "access_token", "auth"} or key.endswith(("-signature", "-credential", "-security-token"))):
                        secrets.update((value, raw_value, quote(value, safe=""), quote_plus(value, safe="")))
        for secret in sorted(secrets, key=len, reverse=True):
            text = text.replace(secret, "[REDACTED]")
        return text

    def redacted_result(self, result: dict) -> dict:
        def clean(value):
            if isinstance(value, str):
                return self.redact(value)
            if isinstance(value, list):
                return [clean(item) for item in value]
            if isinstance(value, dict):
                return {self.redact(str(key)): clean(item) for key, item in value.items()}
            return value

        return clean(result)


def credential_cipher(settings: Settings) -> Fernet:
    if not settings.credential_fernet_key:
        return settings._ephemeral_credential_cipher
    return Fernet(settings.credential_fernet_key.encode("ascii"))


def encode_context(request: TaskRequest, settings: Settings) -> tuple[str | None, str | None]:
    if not request.credentials and request.proxy is None and request.allow_write_actions is None and request.browser_profile_id is None and not request.workflow_success_criteria and not request.upload_sources and not request.upload_origins and not request.allow_file_downloads:
        return None, None
    options = json.dumps({
        "allow_write_actions": request.allow_write_actions,
        "browser_profile_id": request.browser_profile_id,
        "allow_file_downloads": request.allow_file_downloads,
        "upload_origins": request.upload_origins,
        "workflow_success_criteria": [item.model_dump() for item in request.workflow_success_criteria],
        "proxy": request.proxy.model_dump() if request.proxy else None,
    })
    blob = None
    if request.credentials:
        payload = [
            {
                "id": credential.id,
                "origins": credential.origins,
                "username": credential.username.get_secret_value(),
                "password": credential.password.get_secret_value(),
                "totp_secret": credential.totp_secret.get_secret_value() if credential.totp_secret else None,
            }
            for credential in request.credentials
        ]
        blob = credential_cipher(settings).encrypt(json.dumps(payload).encode()).decode("ascii")
    return options, blob


def encode_file_sources(request: TaskRequest, settings: Settings) -> str | None:
    if not request.upload_sources:
        return None
    payload = [{"id": source.id, "url": source.url.get_secret_value(), "filename": source.filename} for source in request.upload_sources]
    return credential_cipher(settings).encrypt(json.dumps(payload).encode()).decode("ascii")


def decode_context(options: str | None, blob: str | None, settings: Settings, *, file_sources_blob: str | None = None) -> TaskContext | None:
    if options is None and blob is None and file_sources_blob is None:
        return None
    data = json.loads(options or "{}")
    credentials = []
    expires_at = None
    if blob is not None:
        cipher = credential_cipher(settings)
        encoded = blob.encode("ascii")
        payload = cipher.decrypt(encoded, ttl=settings.credential_ttl_seconds)
        expires_at = cipher.extract_timestamp(encoded) + settings.credential_ttl_seconds
        if time.time() >= expires_at:
            raise ValueError("Credentials expired")
        credentials = [LoginCredential.model_validate(item) for item in json.loads(payload)]
    sources, sources_expires_at = [], None
    if file_sources_blob is not None:
        cipher = credential_cipher(settings)
        encoded_sources = file_sources_blob.encode("ascii")
        raw_sources = cipher.decrypt(encoded_sources, ttl=settings.file_source_ttl_seconds)
        sources_expires_at = cipher.extract_timestamp(encoded_sources) + settings.file_source_ttl_seconds
        if time.time() >= sources_expires_at:
            raise ValueError("File-source grants expired")
        sources = [UploadSource.model_validate(item) for item in json.loads(raw_sources)]
    return TaskContext(
        allow_write_actions=data.get("allow_write_actions"),
        allow_file_downloads=data.get("allow_file_downloads", False),
        upload_sources=sources, upload_origins=data.get("upload_origins", []),
        file_sources_expires_at=sources_expires_at,
        browser_profile_id=data.get("browser_profile_id"),
        workflow_success_criteria=[WorkflowSuccessCriterion.model_validate(item) for item in data.get("workflow_success_criteria", [])],
        proxy=FixedProxy.model_validate(data["proxy"]) if data.get("proxy") else None,
        credentials=credentials, credential_expires_at=expires_at,
    )
