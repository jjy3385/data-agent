from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: Literal["local", "development", "staging", "production"] = "local"
    admin_db_path: str = "./data/admin.db"

    @field_validator("admin_db_path")
    @classmethod
    def admin_db_path_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("admin_db_path must not be blank")
        return value


def get_settings() -> Settings:
    return Settings()
