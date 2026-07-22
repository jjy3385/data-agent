import os
from pathlib import Path

from sqlalchemy import Engine, URL, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.db.errors import AdminDBUnavailableError


def _ensure_parent_directory_accessible(admin_db_path: str) -> Path:
    path = Path(admin_db_path).resolve()
    parent = path.parent

    if not parent.is_dir():
        raise AdminDBUnavailableError(f"Admin DB parent directory does not exist: {parent}")
    if not os.access(parent, os.W_OK):
        raise AdminDBUnavailableError(f"Admin DB parent directory is not writable: {parent}")

    return path


def build_admin_db_engine(admin_db_path: str) -> Engine:
    """Admin DB 경로 접근을 확인하고 SQLite Engine을 생성한다. 모든 연결에서 Foreign Key 강제를 켠다."""
    path = _ensure_parent_directory_accessible(admin_db_path)

    try:
        url = URL.create("sqlite", database=str(path))
        engine = create_engine(url)
    except Exception as exc:
        raise AdminDBUnavailableError(f"Failed to create Admin DB engine: {exc}") from exc

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def get_sessionmaker(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)
