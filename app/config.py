from pathlib import Path

from cryptography.fernet import Fernet
from pydantic import Field, PrivateAttr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    openai_base_url: str = ""
    model_name: str = ""
    task_api_token: str = ""
    require_task_api_token: bool = False
    app_revision: str = "local"
    enable_write_actions: bool = False
    display_viewer_enabled: bool = False
    display_viewer_token: str = Field(default="", repr=False)
    display_viewer_origin: str = ""
    display_viewer_session_seconds: int = Field(default=900, ge=60, le=3600)
    display_viewer_assets: Path = Path("/opt/posting-novnc")
    display_viewer_max_connections: int = Field(default=2, ge=1, le=2)
    _display_viewer: object = PrivateAttr(default=None)
    credential_fernet_key: str = Field(default="", repr=False)
    _ephemeral_credential_cipher: Fernet = PrivateAttr(default_factory=lambda: Fernet(Fernet.generate_key()))
    credential_ttl_seconds: int = Field(default=900, ge=60, le=3600)
    database_path: Path = Path("data/tasks.db")
    chromium_binary: Path = Path("/usr/bin/chromium")
    chromedriver_binary: Path = Path("/usr/bin/chromedriver")
    browser_window_width: int = Field(default=1024, ge=640, le=3840)
    browser_window_height: int = Field(default=768, ge=480, le=2160)
    max_active_tasks: int = 20
    model_timeout_seconds: int = 45
    browser_timeout_seconds: int = 20
    task_timeout_seconds: int = 180
    max_agent_steps: int = 20
