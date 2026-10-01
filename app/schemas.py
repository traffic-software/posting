from datetime import datetime
from enum import StrEnum
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


def https_origin(value: str) -> str:
    parsed = urlsplit(value)
    host = (parsed.hostname or "").lower().rstrip(".")
    port = parsed.port
    if (
        parsed.scheme != "https" or not host or port == 0
        or parsed.username is not None or parsed.password is not None
        or "\\" in parsed.netloc or "%" in host
    ):
        raise ValueError("Invalid HTTPS origin")
    authority = f"[{host}]" if ":" in host else host
    return f"https://{authority}" + (f":{port}" if port not in (None, 443) else "")


class LoginCredential(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    id: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_-]{0,49}$")
    origins: list[str] = Field(min_length=1, max_length=5)
    username: SecretStr
    password: SecretStr

    @field_validator("origins")
    @classmethod
    def valid_origins(cls, values: list[str]) -> list[str]:
        for value in values:
            parsed = urlsplit(value)
            if len(value) > 500 or parsed.path not in ("", "/") or parsed.query or parsed.fragment:
                raise ValueError("Supply exact HTTPS origins, not login paths")
        return list(dict.fromkeys(https_origin(value) for value in values))

    @field_validator("username", "password")
    @classmethod
    def valid_secret(cls, value: SecretStr) -> SecretStr:
        raw = value.get_secret_value()
        if not raw.strip() or len(raw) > 2000:
            raise ValueError("Invalid credential value")
        return value


class FixedProxy(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    scheme: Literal["http", "socks5"] = "http"
    host: str = Field(min_length=1, max_length=253)
    port: int = Field(ge=1, le=65535, strict=True)

    @field_validator("host")
    @classmethod
    def valid_host(cls, value: str) -> str:
        import ipaddress

        value = value.lower().rstrip(".")
        try:
            ipaddress.ip_address(value)
        except ValueError:
            if not value or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789.-" for character in value):
                raise ValueError("Proxy host must be a hostname or IP, without credentials")
        return value

    @property
    def endpoint(self) -> str:
        host = f"[{self.host}]" if ":" in self.host else self.host
        return f"{host}:{self.port}"


class TaskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    prompt: str = Field(min_length=1, max_length=4000)
    allow_write_actions: bool | None = Field(default=None, strict=True)
    credentials: list[LoginCredential] = Field(default_factory=list, max_length=5)
    proxy: FixedProxy | None = None

    @model_validator(mode="after")
    def valid_credentials(self):
        if self.credentials and self.allow_write_actions is not True:
            raise ValueError("Credentials require task write consent")
        ids = [credential.id for credential in self.credentials]
        if len(ids) != len(set(ids)):
            raise ValueError("Credential IDs must be unique")
        return self

    @field_validator("prompt")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Prompt must not be blank")
        return value.strip()


class TaskAccepted(BaseModel):
    task_id: UUID
    status: TaskStatus


class TaskResponse(TaskAccepted):
    result: dict | None
    error: str | None
    created_at: datetime
    updated_at: datetime
