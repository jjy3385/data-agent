from contextlib import asynccontextmanager
from typing import Any

import pytest

from app.db.schema import prepare_admin_db_schema
from app.db.session import build_admin_db_engine, get_sessionmaker

FAKE_INSPECT_SCHEMA_RESULT: dict[str, Any] = {
    "correlation_id": "fake",
    "schemas": [
        {
            "schema_name": "Production",
            "tables": [
                {
                    "table_name": "Product",
                    "description": "Fake product table for tests.",
                    "columns": [
                        {
                            "column_name": "ProductID",
                            "data_type": "int",
                            "is_nullable": False,
                            "ordinal_position": 1,
                            "description": None,
                        },
                        {
                            "column_name": "Name",
                            "data_type": "nvarchar(50)",
                            "is_nullable": False,
                            "ordinal_position": 2,
                            "description": None,
                        },
                    ],
                    "primary_key": {"columns": ["ProductID"]},
                }
            ],
        }
    ],
    "foreign_keys": [],
    "summary": {"schema_count": 1, "table_count": 1},
}


class FakeMCPClientManager:
    """실제 MCP Server·Docker 없이 Lifespan·Contract 흐름을 검증하기 위한 Fake."""

    def __init__(self) -> None:
        self.unavailable = False
        self.inspect_schema_calls: list[str] = []
        self.execute_readonly_query_calls: list[dict[str, Any]] = []

    async def inspect_schema(self, correlation_id: str) -> dict[str, Any]:
        self.inspect_schema_calls.append(correlation_id)
        return {**FAKE_INSPECT_SCHEMA_RESULT, "correlation_id": correlation_id}

    async def execute_readonly_query(
        self,
        sql: str,
        parameters: list,
        correlation_id: str,
        query_timeout_seconds: int,
        maximum_returned_rows: int,
    ) -> dict[str, Any]:
        call = {
            "sql": sql,
            "parameters": parameters,
            "correlation_id": correlation_id,
            "query_timeout_seconds": query_timeout_seconds,
            "maximum_returned_rows": maximum_returned_rows,
        }
        self.execute_readonly_query_calls.append(call)
        return {
            "correlation_id": correlation_id,
            "columns": ["ProductID"],
            "rows": [[1]],
            "row_count": 1,
            "truncated": False,
            "execution_ms": 1,
        }


def _fake_mcp_lifespan_factory():
    @asynccontextmanager
    async def fake_mcp_lifespan():
        yield FakeMCPClientManager()

    return fake_mcp_lifespan


@pytest.fixture(autouse=True)
def fake_mcp_lifespan(request, monkeypatch):
    """requires_target_db로 표시되지 않은 모든 테스트는 실제 Docker MSSQL·MCP Server 없이
    app.core.lifespan._mcp_lifespan을 Fake로 대체해 동작한다."""
    if "requires_target_db" in request.keywords:
        yield
        return

    monkeypatch.setattr("app.core.lifespan._mcp_lifespan", _fake_mcp_lifespan_factory())
    yield


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
