from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: Literal["local", "development", "staging", "production"] = "local"


def get_settings() -> Settings:
    return Settings()
