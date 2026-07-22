from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, inspect

from app.db.errors import AdminDBUnavailableError

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_ALEMBIC_INI = _REPO_ROOT / "alembic.ini"
_ALEMBIC_SCRIPT_LOCATION = _REPO_ROOT / "alembic"

_REQUIRED_TABLES = ("users", "table_policies", "audit_logs", "error_reports")


def _alembic_config() -> Config:
    config = Config(str(_ALEMBIC_INI))
    config.set_main_option("script_location", str(_ALEMBIC_SCRIPT_LOCATION))
    return config


def _run_migrations(engine: Engine) -> None:
    config = _alembic_config()
    try:
        with engine.connect() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
    except Exception as exc:
        raise AdminDBUnavailableError(f"Admin DB migration failed: {exc}") from exc


def _verify_schema(engine: Engine) -> None:
    config = _alembic_config()
    script = ScriptDirectory.from_config(config)
    head_revision = script.get_current_head()

    try:
        with engine.connect() as connection:
            migration_context = MigrationContext.configure(connection)
            current_revision = migration_context.get_current_revision()
    except Exception as exc:
        raise AdminDBUnavailableError(f"Failed to read Admin DB revision: {exc}") from exc

    if current_revision != head_revision:
        raise AdminDBUnavailableError(
            f"Admin DB schema revision mismatch: expected {head_revision!r}, found {current_revision!r}"
        )

    existing_tables = set(inspect(engine).get_table_names())
    missing_tables = [table for table in _REQUIRED_TABLES if table not in existing_tables]
    if missing_tables:
        raise AdminDBUnavailableError(f"Admin DB is missing required tables: {missing_tables}")


def prepare_admin_db_schema(engine: Engine) -> None:
    """Alembic head까지 Migration을 적용하고 head Revision·필수 테이블 존재를 확인한다.

    실패하면 AdminDBUnavailableError를 발생시킨다.
    """
    _run_migrations(engine)
    _verify_schema(engine)
