import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings


def test_admin_db_path_defaults_to_local_data_dir(monkeypatch):
    monkeypatch.delenv("ADMIN_DB_PATH", raising=False)
    settings = get_settings()
    assert settings.admin_db_path == "./data/admin.db"


def test_admin_db_path_accepts_custom_value(monkeypatch, tmp_path):
    custom_path = str(tmp_path / "custom-admin.db")
    monkeypatch.setenv("ADMIN_DB_PATH", custom_path)
    settings = get_settings()
    assert settings.admin_db_path == custom_path


@pytest.mark.parametrize("value", ["", "   "])
def test_admin_db_path_rejects_blank_value(monkeypatch, value):
    monkeypatch.setenv("ADMIN_DB_PATH", value)
    with pytest.raises(ValidationError):
        Settings()
