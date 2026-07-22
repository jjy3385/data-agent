import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.db.errors import AdminDBUnavailableError
from main import app as main_app


def test_inaccessible_parent_directory_fails_startup(tmp_path, monkeypatch):
    missing_dir_path = tmp_path / "does-not-exist" / "nested" / "admin.db"
    monkeypatch.setenv("ADMIN_DB_PATH", str(missing_dir_path))

    with pytest.raises(AdminDBUnavailableError):
        with TestClient(main_app):
            pass


def test_incompatible_existing_schema_fails_startup(tmp_path, monkeypatch):
    db_path = tmp_path / "admin.db"
    monkeypatch.setenv("ADMIN_DB_PATH", str(db_path))

    # Alembic Migration이 알지 못하는 users 테이블을 미리 만들어 "이미 존재" 충돌을 재현한다.
    connection = sqlite3.connect(db_path)
    connection.execute("CREATE TABLE users (id INTEGER PRIMARY KEY)")
    connection.commit()
    connection.close()

    with pytest.raises(AdminDBUnavailableError):
        with TestClient(main_app):
            pass
