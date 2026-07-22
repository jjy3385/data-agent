import pytest

from app.db.schema import prepare_admin_db_schema
from app.db.session import build_admin_db_engine, get_sessionmaker


@pytest.fixture
def admin_db_path(tmp_path, monkeypatch):
    """ADMIN_DB_PATH를 임시 경로로 지정해 TestClient의 실제 Lifespan이 저장소의 data/admin.db를 오염시키지 않게 한다."""
    path = tmp_path / "admin.db"
    monkeypatch.setenv("ADMIN_DB_PATH", str(path))
    return path


@pytest.fixture
def admin_engine(tmp_path):
    """준비가 끝난 임시 Admin DB Engine. Migration과 최소 Schema 확인이 이미 완료된 상태로 제공한다."""
    engine = build_admin_db_engine(str(tmp_path / "admin.db"))
    prepare_admin_db_schema(engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def admin_session(admin_engine):
    session_factory = get_sessionmaker(admin_engine)
    with session_factory() as session:
        yield session
