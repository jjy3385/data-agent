import pytest
from pydantic import ValidationError

from mcp_server import db

_DUMMY_VALUES = {
    "TARGET_DB_HOST": "test-host",
    "TARGET_DB_PORT": "1433",
    "TARGET_DB_NAME": "TestDB",
    "TARGET_DB_USER": "test_user",
    "TARGET_DB_PASSWORD": "test-password-not-real",
    "TARGET_DB_DRIVER": "ODBC Driver 18 for SQL Server",
    "TARGET_DB_ENCRYPT": "yes",
    "TARGET_DB_TRUST_SERVER_CERTIFICATE": "yes",
}


def _set_all_dummy_env(monkeypatch, overrides=None):
    values = {**_DUMMY_VALUES, **(overrides or {})}
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def test_target_db_settings_loads_from_env(monkeypatch):
    _set_all_dummy_env(monkeypatch)
    settings = db.TargetDBSettings()
    assert settings.host == "test-host"
    assert settings.port == "1433"
    assert settings.name == "TestDB"
    assert settings.user == "test_user"
    assert settings.driver == "ODBC Driver 18 for SQL Server"


@pytest.mark.parametrize("field_env_key", list(_DUMMY_VALUES))
def test_target_db_settings_rejects_blank_values(monkeypatch, field_env_key):
    _set_all_dummy_env(monkeypatch, overrides={field_env_key: "   "})
    with pytest.raises(ValidationError):
        db.TargetDBSettings()


def test_build_connection_string_contains_expected_fragments(monkeypatch):
    _set_all_dummy_env(monkeypatch)
    settings = db.TargetDBSettings()
    connection_string = db._build_connection_string(settings)

    assert "SERVER=test-host,1433" in connection_string
    assert "DATABASE=TestDB" in connection_string
    assert "UID=test_user" in connection_string
    assert "PWD={test-password-not-real}" in connection_string
    assert "ApplicationIntent=ReadOnly" in connection_string
    assert "DRIVER={ODBC Driver 18 for SQL Server}" in connection_string


def test_is_timeout_error_detects_sqlstate():
    import pyodbc

    exc = pyodbc.Error("HYT00", "[Driver] Query timeout expired")
    assert db.is_timeout_error(exc) is True


def test_is_timeout_error_detects_message_substring():
    import pyodbc

    exc = pyodbc.Error("HY000", "[Driver] connection timeout occurred")
    assert db.is_timeout_error(exc) is True


def test_is_timeout_error_false_for_unrelated_error():
    import pyodbc

    exc = pyodbc.Error("42000", "[Driver] Invalid column name 'Foo'")
    assert db.is_timeout_error(exc) is False
