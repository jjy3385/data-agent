import asyncio
from types import SimpleNamespace

import anyio
import pytest
from mcp import McpError
from mcp.types import CONNECTION_CLOSED, ErrorData

from app.mcp import client_manager as client_manager_module
from app.mcp.client_manager import MCPClientManager, MCPToolExecutionError, MCPTransportError

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


_VALID_INSPECT_SCHEMA_STRUCTURED = {
    "correlation_id": "c1",
    "schemas": [],
    "foreign_keys": [],
    "summary": {"schema_count": 0, "table_count": 0},
}

_VALID_EXECUTE_QUERY_STRUCTURED = {
    "correlation_id": "c1",
    "columns": ["ProductID"],
    "rows": [[1]],
    "row_count": 1,
    "truncated": False,
    "execution_ms": 5,
}


class _FakeSession:
    def __init__(self, result=None, exc=None, delay: float = 0.0):
        self._result = result
        self._exc = exc
        self._delay = delay
        self.call_count = 0

    async def call_tool(self, name, arguments):
        self.call_count += 1
        if self._delay:
            await asyncio.sleep(self._delay)
        if self._exc is not None:
            raise self._exc
        return self._result


async def test_inspect_schema_success_returns_validated_dict():
    session = _FakeSession(
        result=SimpleNamespace(isError=False, structuredContent=_VALID_INSPECT_SCHEMA_STRUCTURED, content=[])
    )
    manager = MCPClientManager(session)

    result = await manager.inspect_schema("c1")

    assert result["correlation_id"] == "c1"
    assert result["schemas"] == []
    assert session.call_count == 1


async def test_execute_readonly_query_success_returns_validated_dict():
    session = _FakeSession(
        result=SimpleNamespace(isError=False, structuredContent=_VALID_EXECUTE_QUERY_STRUCTURED, content=[])
    )
    manager = MCPClientManager(session)

    result = await manager.execute_readonly_query(
        sql="SELECT 1",
        parameters=[],
        correlation_id="c1",
        query_timeout_seconds=5,
        maximum_returned_rows=10,
    )

    assert result["row_count"] == 1
    assert result["rows"] == [[1]]


async def test_is_error_result_raises_tool_execution_error_with_safe_fixed_message():
    """원본 TextContent("boom ...")는 그대로 노출되지 않고 고정된 안전 메시지로 치환된다."""
    marker = "SECRET-MARKER-should-not-leak"
    session = _FakeSession(
        result=SimpleNamespace(
            isError=True,
            structuredContent=None,
            content=[SimpleNamespace(text=f"boom {marker} DRIVER=ODBC;PWD=hunter2;SQL=SELECT * FROM Foo")],
        )
    )
    manager = MCPClientManager(session)

    with pytest.raises(MCPToolExecutionError) as excinfo:
        await manager.inspect_schema("c1")

    assert excinfo.value.reason == "tool_error"
    assert str(excinfo.value) == "MCP tool returned an error"
    assert marker not in str(excinfo.value)
    assert "hunter2" not in str(excinfo.value)
    assert "boom" not in str(excinfo.value)


@pytest.mark.parametrize(
    "raw_text",
    [
        "DB query timeout exceeded (5s)",
        "Schema inspection timeout exceeded",
        # FastMCP가 앞에 Tool 실행 오류 Prefix를 붙이는 경우도 부분 문자열로 인식해야 한다.
        "Error executing tool execute_readonly_query: DB query timeout exceeded (7s)",
    ],
)
async def test_tool_error_with_safe_timeout_phrase_is_classified_as_tool_timeout(raw_text):
    """서버가 만든 안전한 Timeout Phrase는 reason="tool_timeout"으로 구분되는 고정 메시지를 받는다."""
    session = _FakeSession(
        result=SimpleNamespace(isError=True, structuredContent=None, content=[SimpleNamespace(text=raw_text)])
    )
    manager = MCPClientManager(session)

    with pytest.raises(MCPToolExecutionError) as excinfo:
        await manager.inspect_schema("c1")

    assert excinfo.value.reason == "tool_timeout"
    assert str(excinfo.value) == "MCP tool reported a timeout"


async def test_tool_error_with_generic_timeout_word_is_not_classified_as_tool_timeout():
    """Allowlist는 "timeout" 단어 포함 여부가 아니라 서버의 고정 Phrase만 인식한다."""
    session = _FakeSession(
        result=SimpleNamespace(
            isError=True,
            structuredContent=None,
            content=[SimpleNamespace(text="Connection timeout while contacting upstream service")],
        )
    )
    manager = MCPClientManager(session)

    with pytest.raises(MCPToolExecutionError) as excinfo:
        await manager.inspect_schema("c1")

    assert excinfo.value.reason == "tool_error"
    assert str(excinfo.value) == "MCP tool returned an error"


async def test_tool_error_without_timeout_text_is_classified_as_generic():
    session = _FakeSession(
        result=SimpleNamespace(isError=True, structuredContent=None, content=[SimpleNamespace(text="Schema inspection failed")])
    )
    manager = MCPClientManager(session)

    with pytest.raises(MCPToolExecutionError) as excinfo:
        await manager.inspect_schema("c1")

    assert excinfo.value.reason == "tool_error"
    assert str(excinfo.value) == "MCP tool returned an error"


async def test_missing_structured_content_raises_invalid_result_contract():
    session = _FakeSession(result=SimpleNamespace(isError=False, structuredContent=None, content=[]))
    manager = MCPClientManager(session)

    with pytest.raises(MCPToolExecutionError) as excinfo:
        await manager.inspect_schema("c1")

    assert excinfo.value.reason == "invalid_result_contract"


async def test_contract_mismatch_raises_invalid_result_contract():
    bad_structured = {"correlation_id": "c1"}  # missing required fields
    session = _FakeSession(result=SimpleNamespace(isError=False, structuredContent=bad_structured, content=[]))
    manager = MCPClientManager(session)

    with pytest.raises(MCPToolExecutionError) as excinfo:
        await manager.inspect_schema("c1")

    assert excinfo.value.reason == "invalid_result_contract"


async def test_call_timeout_marks_manager_unavailable(monkeypatch):
    monkeypatch.setattr(client_manager_module, "MCP_CALL_TIMEOUT_SECONDS", 0.05)
    session = _FakeSession(
        result=SimpleNamespace(isError=False, structuredContent=_VALID_INSPECT_SCHEMA_STRUCTURED, content=[]),
        delay=1.0,
    )
    manager = MCPClientManager(session)

    with pytest.raises(MCPTransportError) as excinfo:
        await manager.inspect_schema("c1")

    assert excinfo.value.reason == "call_timeout"
    assert manager.unavailable is True


async def test_os_error_marks_manager_unavailable():
    session = _FakeSession(exc=ConnectionError("pipe closed"))
    manager = MCPClientManager(session)

    with pytest.raises(MCPTransportError) as excinfo:
        await manager.inspect_schema("c1")

    assert excinfo.value.reason == "connection_closed"
    assert manager.unavailable is True


async def test_mcp_error_connection_closed_marks_manager_unavailable_and_stops_calling_session():
    """실제 MCP SDK가 Transport 단절 시 던지는 McpError(code=CONNECTION_CLOSED)를 재현한다."""
    session = _FakeSession(exc=McpError(ErrorData(code=CONNECTION_CLOSED, message="Connection closed")))
    manager = MCPClientManager(session)

    with pytest.raises(MCPTransportError) as excinfo:
        await manager.inspect_schema("c1")

    assert excinfo.value.reason == "connection_closed"
    assert manager.unavailable is True
    assert session.call_count == 1

    with pytest.raises(MCPTransportError) as excinfo2:
        await manager.inspect_schema("c2")

    assert excinfo2.value.reason == "unavailable"
    assert session.call_count == 1


async def test_mcp_error_with_other_code_is_converted_to_tool_protocol_error():
    """CONNECTION_CLOSED가 아닌 McpError는 Transport 오류로 재해석하지 않지만, MCP SDK 내부
    예외 타입이나 원본 message/data를 호출자에게 그대로 노출하지도 않는다 — 고정된 안전
    메시지의 MCPToolExecutionError(reason="tool_protocol_error")로 변환한다."""
    marker = "SECRET-MARKER-protocol-error-data"
    session = _FakeSession(
        exc=McpError(ErrorData(code=-32601, message=f"Method not found {marker}", data={"detail": marker}))
    )
    manager = MCPClientManager(session)

    with pytest.raises(MCPToolExecutionError) as excinfo:
        await manager.inspect_schema("c1")

    assert excinfo.value.reason == "tool_protocol_error"
    assert str(excinfo.value) == "MCP protocol error"
    assert marker not in str(excinfo.value)
    assert manager.unavailable is False


async def test_mcp_error_with_other_code_does_not_expose_sdk_exception_type():
    session = _FakeSession(exc=McpError(ErrorData(code=-32601, message="Method not found")))
    manager = MCPClientManager(session)

    try:
        await manager.inspect_schema("c1")
        assert False, "expected MCPToolExecutionError"
    except McpError:
        assert False, "raw McpError must not escape MCPClientManager"
    except MCPToolExecutionError as exc:
        assert exc.reason == "tool_protocol_error"


@pytest.mark.parametrize(
    "make_exc",
    [
        lambda: anyio.BrokenResourceError(),
        lambda: anyio.ClosedResourceError(),
        lambda: anyio.EndOfStream(),
    ],
    ids=["BrokenResourceError", "ClosedResourceError", "EndOfStream"],
)
async def test_anyio_transport_exceptions_mark_manager_unavailable_and_stop_calling_session(make_exc):
    session = _FakeSession(exc=make_exc())
    manager = MCPClientManager(session)

    with pytest.raises(MCPTransportError) as excinfo:
        await manager.inspect_schema("c1")

    assert excinfo.value.reason == "connection_closed"
    assert manager.unavailable is True
    assert session.call_count == 1

    with pytest.raises(MCPTransportError) as excinfo2:
        await manager.inspect_schema("c2")

    assert excinfo2.value.reason == "unavailable"
    assert session.call_count == 1


async def test_after_unavailable_further_calls_short_circuit_without_calling_session():
    session = _FakeSession(exc=ConnectionError("pipe closed"))
    manager = MCPClientManager(session)

    with pytest.raises(MCPTransportError):
        await manager.inspect_schema("c1")

    assert session.call_count == 1

    with pytest.raises(MCPTransportError) as excinfo:
        await manager.inspect_schema("c2")

    assert excinfo.value.reason == "unavailable"
    assert session.call_count == 1


async def test_no_auto_reconnect_after_unavailable():
    session = _FakeSession(
        result=SimpleNamespace(isError=False, structuredContent=_VALID_INSPECT_SCHEMA_STRUCTURED, content=[])
    )
    manager = MCPClientManager(session)
    manager._unavailable = True

    with pytest.raises(MCPTransportError) as excinfo:
        await manager.inspect_schema("c1")

    assert excinfo.value.reason == "unavailable"
    assert session.call_count == 0


async def test_concurrent_calls_recheck_unavailable_inside_lock(monkeypatch):
    monkeypatch.setattr(client_manager_module, "MCP_CALL_TIMEOUT_SECONDS", 0.05)
    session = _FakeSession(
        result=SimpleNamespace(isError=False, structuredContent=_VALID_INSPECT_SCHEMA_STRUCTURED, content=[]),
        delay=1.0,
    )
    manager = MCPClientManager(session)

    async def call_a():
        with pytest.raises(MCPTransportError) as excinfo:
            await manager.inspect_schema("a")
        return excinfo.value.reason

    async def call_b():
        await asyncio.sleep(0.01)
        with pytest.raises(MCPTransportError) as excinfo:
            await manager.inspect_schema("b")
        return excinfo.value.reason

    reason_a, reason_b = await asyncio.gather(call_a(), call_b())

    assert reason_a == "call_timeout"
    assert reason_b == "unavailable"
    assert manager.unavailable is True
    assert session.call_count == 1
