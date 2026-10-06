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
    totp_secret: SecretStr | None = None

    @field_validator("totp_secret")
    @classmethod
    def valid_totp_secret(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None:
            return None
        import base64
        import binascii

        raw = value.get_secret_value()
        if len(raw) > 256 or any(char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz234567 \t\r\n\v\f" for char in raw):
            raise ValueError("Invalid Base32 TOTP secret")
        raw = "".join(char for char in raw if char not in " \t\r\n\v\f").upper()
        if not 16 <= len(raw) <= 128 or any(char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567" for char in raw):
            raise ValueError("Invalid Base32 TOTP secret")
        try:
            decoded = base64.b32decode(raw + "=" * (-len(raw) % 8))
        except (ValueError, binascii.Error):
            raise ValueError("Invalid Base32 TOTP secret") from None
        if len(decoded) < 10 or base64.b32encode(decoded).decode().rstrip("=") != raw:
            raise ValueError("Invalid Base32 TOTP secret")
        return SecretStr(raw)

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


class WorkflowSuccessCriterion(BaseModel):
    """Caller-selected visible outcome, not an agent's claim of completion."""
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    origin: str = Field(max_length=500)
    selector: str = Field(min_length=1, max_length=300)
    expected_text: str = Field(min_length=3, max_length=160)

    @field_validator("origin")
    @classmethod
    def exact_origin(cls, value: str) -> str:
        parsed = urlsplit(value)
        if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            raise ValueError("Supply an exact HTTPS origin")
        return https_origin(value)

    @field_validator("selector", "expected_text")
    @classmethod
    def printable_value(cls, value: str) -> str:
        if not value.strip() or any(ord(char) < 32 for char in value):
            raise ValueError("Supply printable outcome criteria")
        return value.strip()


class UploadSource(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    id: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_-]{0,49}$")
    url: SecretStr
    filename: str | None = Field(default=None, max_length=255)

    @field_validator("url")
    @classmethod
    def valid_source_url(cls, value: SecretStr) -> SecretStr:
        raw = value.get_secret_value()
        parsed = urlsplit(raw)
        if (not raw or len(raw) > 4096 or any(ord(char) < 32 or ord(char) == 127 for char in raw)
            or parsed.scheme != "https" or not parsed.hostname or parsed.port == 0
            or parsed.username is not None or parsed.password is not None
            or "\\" in parsed.netloc or "%" in parsed.hostname):
            raise ValueError("Supply a public HTTPS source URL without embedded credentials")
        return value

    @field_validator("filename")
    @classmethod
    def safe_filename(cls, value):
        if value is not None and (not value.strip() or value in {".", ".."} or any(char in value for char in "/\\") or any(ord(char) < 32 or ord(char) == 127 for char in value)):
            raise ValueError("Supply a display filename, not a path")
        return value


class TaskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    prompt: str = Field(min_length=1, max_length=4000)
    allow_write_actions: bool | None = Field(default=None, strict=True)
    credentials: list[LoginCredential] = Field(default_factory=list, max_length=5)
    proxy: FixedProxy | None = None
    browser_profile_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    workflow_success_criteria: list[WorkflowSuccessCriterion] = Field(default_factory=list, max_length=3)
    upload_sources: list[UploadSource] = Field(default_factory=list, max_length=10)
    upload_origins: list[str] = Field(default_factory=list, max_length=10)
    allow_file_downloads: bool = Field(default=False, strict=True)

    @field_validator("upload_origins")
    @classmethod
    def exact_upload_origins(cls, values):
        return LoginCredential.valid_origins(values)

    @field_validator("proxy", mode="before")
    @classmethod
    def proxy_disabled(cls, value):
        if value is not None:
            raise ValueError("Task proxies are disabled")
        return value

    @model_validator(mode="after")
    def valid_credentials(self):
        if self.credentials and self.allow_write_actions is not True:
            raise ValueError("Credentials require task write consent")
        ids = [credential.id for credential in self.credentials]
        if len(ids) != len(set(ids)):
            raise ValueError("Credential IDs must be unique")
        source_ids = [source.id for source in self.upload_sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("Upload source IDs must be unique")
        if self.upload_sources and not self.upload_origins:
            raise ValueError("Upload sources require explicit destination origins")
        if (self.upload_sources or self.upload_origins) and self.allow_write_actions is not True:
            raise ValueError("File uploads require task write consent")
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


class ArtifactSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    id: str = Field(pattern=r"^[a-f0-9]{32}$")
    name: str = Field(max_length=255)
    size_bytes: int = Field(ge=0)
    media_type: str = Field(max_length=120)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    download_url: str = Field(max_length=2048, repr=False)
    expires_at: datetime


class TaskResponse(TaskAccepted):
    result: dict | None
    artifacts: list[ArtifactSummary] = Field(default_factory=list, max_length=50)
    error: str | None
    created_at: datetime
    updated_at: datetime
