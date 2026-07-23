"""requires_target_db로 표시된 테스트만 실행 중인 Docker AdventureWorks2022가 필요하다.

이 파일의 어떤 테스트도 TARGET_DB_* 자격 증명 값을 출력하거나 assert 메시지에 포함하지 않는다.
"""

import asyncio
import subprocess
import sys

import pyodbc
import pytest

from mcp_server import db, readonly_query_executor
from mcp_server.tools.execute_readonly_query import execute_readonly_query
from mcp_server.tools.inspect_schema import inspect_schema

pytestmark = [pytest.mark.requires_target_db, pytest.mark.anyio]


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def test_inspect_schema_returns_adventureworks_user_schemas():
    result = await inspect_schema("test-inspect-schema")

    assert result["summary"]["schema_count"] > 0
    assert result["summary"]["table_count"] > 0
    schema_names = {schema["schema_name"] for schema in result["schemas"]}
    assert "Production" in schema_names

    production = next(s for s in result["schemas"] if s["schema_name"] == "Production")
    product_table = next(t for t in production["tables"] if t["table_name"] == "Product")
    assert product_table["primary_key"] == {"columns": ["ProductID"]}
    column_names = [c["column_name"] for c in product_table["columns"]]
    assert "ProductID" in column_names
    assert "Name" in column_names

    system_schema_names = {"sys", "INFORMATION_SCHEMA", "guest"}
    assert not (schema_names & system_schema_names)
    assert not any(name.startswith("db_") for name in schema_names)


async def test_execute_readonly_query_enforces_maximum_returned_rows():
    result = await execute_readonly_query(
        sql="SELECT ProductID FROM Production.Product ORDER BY ProductID",
        parameters=[],
        correlation_id="test-row-limit",
        query_timeout_seconds=5,
        maximum_returned_rows=3,
    )

    assert result["row_count"] == 3
    assert result["truncated"] is True
    assert len(result["rows"]) == 3


async def test_execute_readonly_query_binds_parameters():
    result = await execute_readonly_query(
        sql="SELECT ProductID, Name FROM Production.Product WHERE ProductID = ?",
        parameters=[680],
        correlation_id="test-param-binding",
        query_timeout_seconds=5,
        maximum_returned_rows=10,
    )

    assert result["row_count"] == 1
    assert result["rows"][0][0] == 680


async def test_execute_readonly_query_returns_untruncated_when_within_limit():
    result = await execute_readonly_query(
        sql="SELECT Name FROM Production.ProductCategory",
        parameters=[],
        correlation_id="test-no-truncation",
        query_timeout_seconds=5,
        maximum_returned_rows=500,
    )

    assert result["truncated"] is False
    assert result["row_count"] == len(result["rows"])


def test_data_agent_ro_account_rejects_write_at_db_level():
    """앱 레벨 SQL 안전성 검사를 우회해 data_agent_ro 계정 자체의 DB 권한을 직접 검증한다.
    WHERE 1 = 0으로 어떤 행도 대상이 되지 않아 권한이 있어도 부작용이 없다(Plan 7절)."""
    connection = db.get_connection()
    try:
        cursor = connection.cursor()
        with pytest.raises(pyodbc.Error) as excinfo:
            cursor.execute("UPDATE Production.Product SET Name = Name WHERE 1 = 0")
        assert excinfo.value.args[0] == "42000"
    finally:
        connection.close()


def test_execute_sets_connection_timeout_to_query_timeout_seconds(monkeypatch):
    """readonly_query_executor.execute()가 실제 pyodbc Connection에 connection.timeout을 설정하는지 확인한다."""
    real_get_connection = db.get_connection
    recorded = {}

    class _TimeoutRecordingConnectionProxy:
        def __init__(self, connection):
            object.__setattr__(self, "_connection", connection)

        def __getattr__(self, name):
            return getattr(self._connection, name)

        def __setattr__(self, name, value):
            if name == "timeout":
                recorded["timeout"] = value
            setattr(self._connection, name, value)

    def _wrapped_get_connection():
        return _TimeoutRecordingConnectionProxy(real_get_connection())

    monkeypatch.setattr(readonly_query_executor.db, "get_connection", _wrapped_get_connection)

    readonly_query_executor.execute(
        sql="SELECT 1 AS n",
        parameters=[],
        query_timeout_seconds=7,
        maximum_returned_rows=10,
    )

    assert recorded["timeout"] == 7


async def test_mcp_lifecycle_smoke_end_to_end():
    """실제 stdio 하위 프로세스를 기동해 Startup, Tool Discovery, Contract 검증, 두 Tool 호출, 정리까지 확인한다."""
    from app.mcp.lifecycle import mcp_lifespan

    async with mcp_lifespan() as manager:
        schema_result = await manager.inspect_schema("lifecycle-smoke")
        assert schema_result["summary"]["table_count"] > 0

        query_result = await manager.execute_readonly_query(
            sql="SELECT COUNT(*) AS n FROM Production.Product",
            parameters=[],
            correlation_id="lifecycle-smoke",
            query_timeout_seconds=5,
            maximum_returned_rows=10,
        )
        assert query_result["row_count"] == 1
        assert manager.unavailable is False


def test_real_child_process_prioritizes_os_env_override_over_dotenv():
    """부모(테스트) 프로세스의 TARGET_DB_USER OS 환경변수를 존재하지 않는 로그인으로 덮어써
    자식 MCP Server subprocess에 전달한다. .env의 올바른 data_agent_ro 대신 이 값이 실제로
    쓰였다면 자가진단이 빠르게(로그인 실패) 거부되어야 한다 — 느린 DNS/연결 Timeout이 아니라
    명확한 인증 실패로 OS 환경변수 우선순위가 자식 프로세스에서도 성립함을 확인한다."""
    import os
    from pathlib import Path

    bogus_login = "definitely_not_a_real_login_xyz"
    env = os.environ.copy()
    env["TARGET_DB_USER"] = bogus_login
    repo_root = Path(__file__).resolve().parent.parent

    result = subprocess.run(
        [sys.executable, "-m", "mcp_server.server"],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert result.returncode == 1
    assert bogus_login not in result.stdout
    assert bogus_login not in result.stderr
    assert result.stdout == ""


async def test_mid_call_subprocess_termination_raises_transport_error_and_marks_unavailable(monkeypatch):
    """실제 MCP 하위 프로세스를 Tool 호출이 진행되는 도중 강제 종료해 stdio 종료 경로를 검증한다.

    Command Line Pattern으로 시스템 전체 프로세스를 찾지 않는다. 대신 MCP SDK가 실제 자식
    프로세스를 생성하는 지점(`mcp.client.stdio._create_platform_compatible_process`)을 감싸
    이 테스트가 직접 기동한 정확한 `anyio.abc.Process` 객체 하나만 캡처하고, 그 객체의
    `kill()`만 호출한다 — PID 검색이나 이름 매칭이 없으므로 사용자의 다른 MCP Server나 병렬
    테스트 프로세스를 건드릴 수 없다. `Process.kill()`은 플랫폼 독립적이라 Windows 전용 skip도
    없앴다."""
    import mcp.client.stdio as stdio_module

    from app.mcp.client_manager import MCPTransportError
    from app.mcp.lifecycle import mcp_lifespan

    captured: dict[str, object] = {}
    original_create_process = stdio_module._create_platform_compatible_process

    async def _capturing_create_process(*args, **kwargs):
        process = await original_create_process(*args, **kwargs)
        captured["process"] = process
        return process

    monkeypatch.setattr(stdio_module, "_create_platform_compatible_process", _capturing_create_process)

    async def _kill_captured_process_after_delay() -> None:
        await asyncio.sleep(0.5)
        process = captured.get("process")
        if process is None:
            return
        process.kill()

    kill_task: asyncio.Task | None = None
    try:
        async with mcp_lifespan() as manager:
            await manager.inspect_schema("pre-kill-check")

            # mcp_lifespan()이 성공했다면 stdio_client가 정확히 한 번 자식 프로세스를
            # 생성했어야 한다. 캡처하지 못했다면 어떤 프로세스도 건드리지 않고 테스트를
            # 실패시킨다(요구사항: PID를 하나로 특정할 수 없으면 실패).
            assert "process" in captured, "child MCP server process was not captured; refusing to kill anything"

            kill_task = asyncio.create_task(_kill_captured_process_after_delay())

            heavy_sql = (
                "SELECT a.name AS n1, b.name AS n2 "
                "FROM sys.all_objects a CROSS JOIN sys.all_objects b ORDER BY a.name, b.name"
            )
            with pytest.raises(MCPTransportError) as excinfo:
                await manager.execute_readonly_query(
                    sql=heavy_sql,
                    parameters=[],
                    correlation_id="mid-call-kill-test",
                    query_timeout_seconds=15,
                    maximum_returned_rows=500,
                )

            assert excinfo.value.reason == "connection_closed"
            assert manager.unavailable is True

            with pytest.raises(MCPTransportError) as excinfo2:
                await manager.inspect_schema("after-kill")
            assert excinfo2.value.reason == "unavailable"

            await kill_task
            kill_task = None
    finally:
        # 테스트 실패·Timeout 때도 캡처한 자식 프로세스가 남지 않도록 정리한다.
        if kill_task is not None:
            kill_task.cancel()
        process = captured.get("process")
        if process is not None and process.returncode is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass


def test_app_startup_with_real_mcp_populates_state_and_cleans_up_on_shutdown(admin_db_path):
    """Fake 없이 main_app 전체 Lifespan(Admin DB + 실제 MCP Server subprocess)을 기동해
    app.state가 채워지고 종료 시 하위 프로세스가 정리되는지 확인한다."""
    from fastapi.testclient import TestClient

    from main import app as main_app

    with TestClient(main_app) as client:
        response = client.get("/health")
        assert response.status_code == 200

        manager = main_app.state.mcp_client_manager
        assert manager is not None
        assert manager.unavailable is False

        catalog = main_app.state.physical_metadata_catalog
        assert catalog.get_table("Production", "Product") is not None
