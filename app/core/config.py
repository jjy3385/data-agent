from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_REPO_ROOT / ".env", extra="ignore")

    app_env: Literal["local", "development", "staging", "production"] = "local"
    admin_db_path: str = "./data/admin.db"

    llm_provider: str | None = None
    llm_model: str | None = None
    llm_api_key: str | None = None
    llm_base_url: str | None = None

    @field_validator("admin_db_path")
    @classmethod
    def admin_db_path_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("admin_db_path must not be blank")
        return value


def get_settings() -> Settings:
    return Settings()
