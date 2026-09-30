from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    openai_base_url: str = ""
    model_name: str = ""
    task_api_token: str = ""
    allowed_hosts: str = ""
    enable_write_actions: bool = False
    database_path: Path = Path("data/tasks.db")
    selenium_remote_url: str = "http://selenium:4444/wd/hub"
    max_active_tasks: int = 20
    model_timeout_seconds: int = 45
    browser_timeout_seconds: int = 20
    task_timeout_seconds: int = 180
    max_agent_steps: int = 20

    @property
    def host_allowlist(self) -> frozenset[str]:
        return frozenset(host.strip().lower().rstrip(".") for host in self.allowed_hosts.split(",") if host.strip())
