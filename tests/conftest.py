import os
from contextlib import asynccontextmanager
from typing import Any

import pytest

from app.db.schema import prepare_admin_db_schema
from app.db.session import build_admin_db_engine, get_sessionmaker
from app.services.llm_client import LLMUnavailableError, is_configured

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
                        {
                            "column_name": "SafetyStockLevel",
                            "data_type": "smallint",
                            "is_nullable": False,
                            "ordinal_position": 3,
                            "description": None,
                        },
                    ],
                    "primary_key": {"columns": ["ProductID"]},
                },
                {
                    "table_name": "ProductInventory",
                    "description": "Fake product inventory table for tests.",
                    "columns": [
                        {
                            "column_name": "ProductID",
                            "data_type": "int",
                            "is_nullable": False,
                            "ordinal_position": 1,
                            "description": None,
                        },
                        {
                            "column_name": "LocationID",
                            "data_type": "smallint",
                            "is_nullable": False,
                            "ordinal_position": 2,
                            "description": None,
                        },
                        {
                            "column_name": "Quantity",
                            "data_type": "smallint",
                            "is_nullable": False,
                            "ordinal_position": 3,
                            "description": None,
                        },
                    ],
                    "primary_key": {"columns": ["ProductID", "LocationID"]},
                },
            ],
        }
    ],
    "foreign_keys": [
        {
            "foreign_key_name": "FK_ProductInventory_Product",
            "source_schema": "Production",
            "source_table": "ProductInventory",
            "source_columns": ["ProductID"],
            "target_schema": "Production",
            "target_table": "Product",
            "target_columns": ["ProductID"],
        }
    ],
    "summary": {"schema_count": 1, "table_count": 2},
}


class FakeLLMClient:
    """LLMClient Protocol을 구현하는 결정적 Fake. 실제 LLM·네트워크를 사용하지 않는다."""

    def __init__(
        self,
        *,
        json_responses: list[dict[str, Any]] | None = None,
        text_responses: list[str] | None = None,
        fail_with: Exception | None = None,
    ) -> None:
        self._json_responses = list(json_responses or [])
        self._text_responses = list(text_responses or [])
        self._fail_with = fail_with
        self.json_calls: list[tuple[str, str, int]] = []
        self.text_calls: list[tuple[str, str, int]] = []

    async def complete_json(
        self, system_prompt: str, user_prompt: str, max_completion_tokens: int
    ) -> dict[str, Any]:
        self.json_calls.append((system_prompt, user_prompt, max_completion_tokens))
        if self._fail_with is not None:
            raise self._fail_with
        if not self._json_responses:
            raise LLMUnavailableError("FakeLLMClient has no queued JSON response")
        return self._json_responses.pop(0)

    async def complete_text(
        self, system_prompt: str, user_prompt: str, max_completion_tokens: int
    ) -> str:
        self.text_calls.append((system_prompt, user_prompt, max_completion_tokens))
        if self._fail_with is not None:
            raise self._fail_with
        if not self._text_responses:
            raise LLMUnavailableError("FakeLLMClient has no queued text response")
        return self._text_responses.pop(0)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """RUN_LLM_TESTS=1이고 실제 LLM 설정이 유효할 때만 requires_llm 테스트를 실행한다."""
    del config
    run_llm_tests = os.environ.get("RUN_LLM_TESTS") == "1"
    llm_ready = run_llm_tests and is_configured()
    if llm_ready:
        return

    skip_marker = pytest.mark.skip(
        reason="requires_llm: RUN_LLM_TESTS=1과 유효한 LLM 설정이 모두 필요합니다."
    )
    for item in items:
        if "requires_llm" in item.keywords:
            item.add_marker(skip_marker)


class FakeMCPClientManager:
    """실제 MCP Server·Docker 없이 Lifespan·Contract 흐름을 검증하기 위한 Fake."""

    def __init__(self, *, execute_error: Exception | None = None) -> None:
        self.unavailable = False
        self.inspect_schema_calls: list[str] = []
        self.execute_readonly_query_calls: list[dict[str, Any]] = []
        self._execute_error = execute_error

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
        if self._execute_error is not None:
            raise self._execute_error
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
def anyio_backend():
    return "asyncio"


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
