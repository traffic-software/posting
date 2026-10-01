import json
import time
import threading
from collections.abc import Callable
from dataclasses import dataclass, field

from cryptography.fernet import Fernet

from app.config import Settings
from app.schemas import FixedProxy, LoginCredential, TaskRequest


@dataclass(repr=False)
class TaskContext:
    allow_write_actions: bool | None = None
    proxy: FixedProxy | None = None
    credentials: list[LoginCredential] = field(default_factory=list)
    credential_expires_at: float | None = None
    cancelled: threading.Event = field(default_factory=threading.Event)
    _browser_lock: threading.Lock = field(default_factory=threading.Lock)
    _browser_close: Callable | None = None

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
        try:
            self.close_browser()
        finally:
            self.credentials.clear()

    def redact(self, text: str) -> str:
        secrets = {
            secret.get_secret_value()
            for credential in self.credentials
            for secret in (credential.username, credential.password)
        }
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
        raise ValueError("Credential encryption is not configured")
    return Fernet(settings.credential_fernet_key.encode("ascii"))


def encode_context(request: TaskRequest, settings: Settings) -> tuple[str | None, str | None]:
    if not request.credentials and request.proxy is None and request.allow_write_actions is None:
        return None, None
    options = json.dumps({
        "allow_write_actions": request.allow_write_actions,
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
            }
            for credential in request.credentials
        ]
        blob = credential_cipher(settings).encrypt(json.dumps(payload).encode()).decode("ascii")
    return options, blob


def decode_context(options: str | None, blob: str | None, settings: Settings) -> TaskContext | None:
    if options is None and blob is None:
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
    return TaskContext(
        allow_write_actions=data.get("allow_write_actions"),
        proxy=FixedProxy.model_validate(data["proxy"]) if data.get("proxy") else None,
        credentials=credentials, credential_expires_at=expires_at,
    )
