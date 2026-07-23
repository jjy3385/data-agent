from pathlib import Path

import pyodbc
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _REPO_ROOT / ".env"

CONNECT_TIMEOUT_SECONDS = 5
SCHEMA_INSPECTION_TIMEOUT_SECONDS = 15

_TIMEOUT_SQLSTATES = {"HYT00", "HYT01"}


class TargetDBSettings(BaseSettings):
    """대상 DB(MSSQL) 접속 설정. mcp_server 밖에서는 이 설정을 소유하지 않는다."""

    model_config = SettingsConfigDict(
        env_prefix="TARGET_DB_",
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str
    port: str
    name: str
    user: str
    password: str
    driver: str
    encrypt: str
    trust_server_certificate: str

    @field_validator("host", "port", "name", "user", "password", "driver", "encrypt", "trust_server_certificate")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("TARGET_DB_* values must not be blank")
        return value


def _build_connection_string(settings: TargetDBSettings) -> str:
    return (
        f"DRIVER={{{settings.driver}}};"
        f"SERVER={settings.host},{settings.port};"
        f"DATABASE={settings.name};"
        f"UID={settings.user};"
        f"PWD={{{settings.password}}};"
        f"Encrypt={settings.encrypt};"
        f"TrustServerCertificate={settings.trust_server_certificate};"
        "ApplicationIntent=ReadOnly;"
    )


def get_connection() -> pyodbc.Connection:
    """대상 DB 연결을 새로 연다. 연결 실패 메시지는 Connection String을 포함하지 않도록 정제한다."""
    settings = TargetDBSettings()
    connection_string = _build_connection_string(settings)
    try:
        return pyodbc.connect(connection_string, timeout=CONNECT_TIMEOUT_SECONDS, autocommit=True)
    except pyodbc.Error as exc:
        raise ConnectionError("Failed to connect to target database") from exc


def verify_connection() -> None:
    """Settings 검증과 대상 DB 연결 가능 여부를 1회 확인한다. 실패 시 예외를 던진다."""
    connection = get_connection()
    connection.close()


def is_timeout_error(exc: pyodbc.Error) -> bool:
    sqlstate = exc.args[0] if exc.args else ""
    message = str(exc).lower()
    return sqlstate in _TIMEOUT_SQLSTATES or "timeout" in message
