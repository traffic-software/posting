from pathlib import Path

from pydantic import Field
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
    credential_fernet_key: str = Field(default="", repr=False)
    credential_ttl_seconds: int = Field(default=900, ge=60, le=3600)
    database_path: Path = Path("data/tasks.db")
    selenium_remote_url: str = "http://selenium:4444/wd/hub"
    max_active_tasks: int = 20
    model_timeout_seconds: int = 45
    browser_timeout_seconds: int = 20
    task_timeout_seconds: int = 180
    max_agent_steps: int = 20
