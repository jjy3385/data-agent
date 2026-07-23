import asyncio
from typing import Any, Protocol

import anyio
from mcp import McpError
from mcp.types import CONNECTION_CLOSED
from pydantic import BaseModel, ValidationError

from app.services.schema_collector import ForeignKeyMetadata, SchemaMetadata

MCP_CALL_TIMEOUT_SECONDS = 20

_UNAVAILABLE_MESSAGE = "MCP session is unavailable after a previous timeout or transport failure"
_TRANSPORT_CLOSED_MESSAGE = "MCP transport connection closed"
_SAFE_TOOL_ERROR_MESSAGE = "MCP tool returned an error"
_SAFE_TOOL_TIMEOUT_MESSAGE = "MCP tool reported a timeout"
_SAFE_PROTOCOL_ERROR_MESSAGE = "MCP protocol error"

_TRANSPORT_CLOSED_EXCEPTIONS = (
    OSError,
    EOFError,
    anyio.BrokenResourceError,
    anyio.ClosedResourceError,
    anyio.EndOfStream,
)

# mcp_server가 실제로 만드는 안전한 Timeout 메시지의 고정 Phrase만 인식한다(자유 텍스트의
# "timeout" 단어 포함 여부로 판정하지 않는다). FastMCP가 앞에 Tool 실행 오류 Prefix를 붙일 수
# 있으므로 부분 문자열 포함으로 확인한다.
_TIMEOUT_SAFE_PHRASES = (
    "DB query timeout exceeded",
    "Schema inspection timeout exceeded",
)


class MCPStartupError(RuntimeError):
    """MCP 실행 경계 준비(Startup·Tool Discovery·Contract 검증) 실패 시 발생한다."""

    def __init__(self, message: str, *, reason: str) -> None:
        super().__init__(message)
        self.reason = reason


class MCPToolExecutionError(RuntimeError):
    """Tool 호출은 성공했으나 결과가 오류이거나 Contract를 만족하지 않을 때 발생한다."""

    def __init__(self, message: str, *, reason: str) -> None:
        super().__init__(message)
        self.reason = reason


class MCPTransportError(RuntimeError):
    """MCP Call Timeout 또는 Session·Transport 단절 시 발생한다."""

    def __init__(self, message: str, *, reason: str) -> None:
        super().__init__(message)
        self.reason = reason


class _CallToolSession(Protocol):
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any: ...


class _InspectSchemaToolResult(BaseModel):
    correlation_id: str
    schemas: list[SchemaMetadata]
    foreign_keys: list[ForeignKeyMetadata]
    summary: dict[str, int]


class _ExecuteReadonlyQueryToolResult(BaseModel):
    correlation_id: str
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    truncated: bool
    execution_ms: int


def _extract_error_text(result: Any) -> str:
    parts = []
    for item in getattr(result, "content", None) or []:
        text = getattr(item, "text", None)
        if text:
            parts.append(text)
    return " ".join(parts)


def _classify_tool_error(result: Any) -> tuple[str, str]:
    """Tool의 원본 오류 TextContent를 그대로 노출하지 않는다. mcp_server가 만드는 안전한
    Timeout Phrase만 Allowlist로 인식해 (고정 메시지, reason) 쌍으로 치환하고, 그 외에는
    일반 고정 메시지와 reason="tool_error"를 사용한다."""
    raw_text = _extract_error_text(result)
    if any(phrase in raw_text for phrase in _TIMEOUT_SAFE_PHRASES):
        return _SAFE_TOOL_TIMEOUT_MESSAGE, "tool_timeout"
    return _SAFE_TOOL_ERROR_MESSAGE, "tool_error"


class MCPClientManager:
    """단일 MCP ClientSession을 감싸 Backend에 Tool 호출 경계를 제공한다."""

    def __init__(self, session: _CallToolSession) -> None:
        self._session = session
        self._lock = asyncio.Lock()
        self._unavailable = False

    @property
    def unavailable(self) -> bool:
        return self._unavailable

    async def inspect_schema(self, correlation_id: str) -> dict[str, Any]:
        result = await self._call_tool("inspect_schema", {"correlation_id": correlation_id})
        return self._parse_result(result, _InspectSchemaToolResult, "inspect_schema")

    async def execute_readonly_query(
        self,
        sql: str,
        parameters: list,
        correlation_id: str,
        query_timeout_seconds: int,
        maximum_returned_rows: int,
    ) -> dict[str, Any]:
        arguments = {
            "sql": sql,
            "parameters": parameters,
            "correlation_id": correlation_id,
            "query_timeout_seconds": query_timeout_seconds,
            "maximum_returned_rows": maximum_returned_rows,
        }
        result = await self._call_tool("execute_readonly_query", arguments)
        return self._parse_result(result, _ExecuteReadonlyQueryToolResult, "execute_readonly_query")

    async def _call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        if self._unavailable:
            raise MCPTransportError(_UNAVAILABLE_MESSAGE, reason="unavailable")

        async with self._lock:
            if self._unavailable:
                raise MCPTransportError(_UNAVAILABLE_MESSAGE, reason="unavailable")

            try:
                return await asyncio.wait_for(
                    self._session.call_tool(name, arguments),
                    timeout=MCP_CALL_TIMEOUT_SECONDS,
                )
            except TimeoutError as exc:
                self._unavailable = True
                raise MCPTransportError(
                    f"MCP call timeout after {MCP_CALL_TIMEOUT_SECONDS}s", reason="call_timeout"
                ) from exc
            except McpError as exc:
                if exc.error.code == CONNECTION_CLOSED:
                    self._unavailable = True
                    raise MCPTransportError(_TRANSPORT_CLOSED_MESSAGE, reason="connection_closed") from exc
                raise MCPToolExecutionError(_SAFE_PROTOCOL_ERROR_MESSAGE, reason="tool_protocol_error") from exc
            except _TRANSPORT_CLOSED_EXCEPTIONS as exc:
                self._unavailable = True
                raise MCPTransportError(_TRANSPORT_CLOSED_MESSAGE, reason="connection_closed") from exc

    @staticmethod
    def _parse_result(result: Any, model: type[BaseModel], tool_name: str) -> dict[str, Any]:
        if getattr(result, "isError", False):
            message, reason = _classify_tool_error(result)
            raise MCPToolExecutionError(message, reason=reason)

        structured = getattr(result, "structuredContent", None)
        if structured is None:
            raise MCPToolExecutionError(
                f"{tool_name} result missing structuredContent", reason="invalid_result_contract"
            )

        try:
            validated = model.model_validate(structured)
        except ValidationError as exc:
            raise MCPToolExecutionError(
                f"{tool_name} result failed contract validation", reason="invalid_result_contract"
            ) from exc

        return validated.model_dump()
