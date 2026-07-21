import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings


def test_app_env_defaults_to_local(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    settings = get_settings()
    assert settings.app_env == "local"


@pytest.mark.parametrize("value", ["development", "staging", "production"])
def test_app_env_accepts_allowed_values(monkeypatch, value):
    monkeypatch.setenv("APP_ENV", value)
    settings = get_settings()
    assert settings.app_env == value


def test_app_env_rejects_invalid_value(monkeypatch):
    monkeypatch.setenv("APP_ENV", "invalid")
    with pytest.raises(ValidationError):
        Settings()
