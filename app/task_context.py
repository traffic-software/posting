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
    _totp_codes: set[str] = field(default_factory=set)
    _totp_attempts: dict[str, set[int]] = field(default_factory=dict)
    _secret_lock: threading.Lock = field(default_factory=threading.Lock)
    _observations: list[dict] = field(default_factory=list)
    _observation_lock: threading.Lock = field(default_factory=threading.Lock)

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
            self.clear_sensitive_state()

    def record_observation(self, tool: str, outcome: str, detail: str) -> None:
        entry = {"tool": tool, "outcome": outcome, "detail": self.redact(detail)[:500]}
        with self._observation_lock:
            if not self.cancelled.is_set():
                self._observations.append(entry)
                del self._observations[:-12]

    def observations(self) -> list[dict]:
        with self._observation_lock:
            entries = [dict(entry) for entry in self._observations]
        return self.redacted_result({"events": entries})["events"]

    def clear_sensitive_state(self) -> None:
        with self._observation_lock:
            self._observations.clear()
        with self._secret_lock:
            self.credentials.clear()
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
        with self._secret_lock:
            secrets = self._totp_codes | {
                secret.get_secret_value()
                for credential in self.credentials
                for secret in (credential.username, credential.password, credential.totp_secret)
                if secret is not None
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
        return settings._ephemeral_credential_cipher
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
                "totp_secret": credential.totp_secret.get_secret_value() if credential.totp_secret else None,
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
