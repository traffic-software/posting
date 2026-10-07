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
    enable_browser_vision: bool = False
    enable_web_search: bool = False
    cloudflare_account_id: str = Field(default="", pattern=r"^(?:[a-fA-F0-9]{32})?$")
    cloudflare_api_token: str = Field(default="", repr=False)
    cloudflare_web_search_gateway: str = Field(default="default", pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    cloudflare_web_search_provider: str = Field(default="ceramic", pattern=r"^(ceramic|exa|linkup)$")
    web_search_timeout_seconds: float = Field(default=10, ge=1, le=30)
    max_web_search_calls: int = Field(default=3, ge=1, le=10)
    enable_workflow_memory: bool = False
    workflow_memory_limit: int = Field(default=100, ge=1, le=500)
    workflow_memory_days: int = Field(default=90, ge=1, le=365)
    _workflow_store: object = PrivateAttr(default=None)
    enable_file_transfers: bool = False
    artifact_root: Path = Path("data/artifacts")
    artifact_public_base_url: str = ""
    artifact_link_signing_key: str = Field(default="", repr=False)
    artifact_retention_seconds: int = Field(default=86400, ge=60, le=2592000)
    artifact_max_file_bytes: int = Field(default=512 * 1024 * 1024, ge=1)
    artifact_max_task_bytes: int = Field(default=1024 * 1024 * 1024, ge=1)
    artifact_max_storage_bytes: int = Field(default=5 * 1024 * 1024 * 1024, ge=1)
    artifact_max_files_per_task: int = Field(default=10, ge=1, le=50)
    artifact_max_objects: int = Field(default=1000, ge=10, le=100000)
    file_source_ttl_seconds: int = Field(default=3600, ge=60, le=86400)
    file_network_timeout_seconds: float = Field(default=10, ge=1, le=60)
    file_download_wait_seconds: float = Field(default=10, ge=1, le=60)
    _artifact_manager: object = PrivateAttr(default=None)
    display_viewer_enabled: bool = False
    display_viewer_token: str = Field(default="", repr=False)
    display_viewer_origin: str = ""
    display_viewer_session_seconds: int = Field(default=1800, ge=60, le=3600)
    display_viewer_assets: Path = Path("/opt/posting-novnc")
    display_viewer_max_connections: int = Field(default=2, ge=1, le=2)
    _display_viewer: object = PrivateAttr(default=None)
    _browser_sessions: object = PrivateAttr(default=None)
    browser_profiles_root: Path = Path("data/browser_profiles")
    manual_browser_seconds: int = Field(default=1800, ge=60, le=7200)
    task_manual_seconds: int = Field(default=600, ge=30, le=1800)
    manual_disconnected_grace_seconds: int = Field(default=60, ge=10, le=300)
    credential_fernet_key: str = Field(default="", repr=False)
    _ephemeral_credential_cipher: Fernet = PrivateAttr(default_factory=lambda: Fernet(Fernet.generate_key()))
    credential_ttl_seconds: int = Field(default=900, ge=60, le=3600)
    database_path: Path = Path("data/tasks.db")
    chromium_binary: Path = Path("/usr/bin/chromium")
    chromedriver_binary: Path = Path("/usr/bin/chromedriver")
    browser_window_width: int = Field(default=1920, ge=640, le=3840)
    browser_window_height: int = Field(default=1080, ge=480, le=2160)
    max_active_tasks: int = 20
    model_timeout_seconds: int = 45
    browser_timeout_seconds: int = 20
    task_timeout_seconds: int = 180
    max_agent_steps: int = 20
