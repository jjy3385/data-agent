import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_server import db
from mcp_server.tools.execute_readonly_query import execute_readonly_query as _execute_readonly_query
from mcp_server.tools.inspect_schema import inspect_schema as _inspect_schema

mcp = FastMCP("data-agent-mssql")


@mcp.tool(structured_output=True)
async def inspect_schema(correlation_id: str) -> dict[str, Any]:
    """AdventureWorks2022의 사용자 정의 Schema·Table·Column·Key·설명을 조회한다."""
    return await _inspect_schema(correlation_id)


@mcp.tool(structured_output=True)
async def execute_readonly_query(
    sql: str,
    parameters: list,
    correlation_id: str,
    query_timeout_seconds: int,
    maximum_returned_rows: int,
) -> dict[str, Any]:
    """SELECT 전용 쿼리를 대상 DB에서 실행하고 결과를 반환한다."""
    return await _execute_readonly_query(
        sql, parameters, correlation_id, query_timeout_seconds, maximum_returned_rows
    )


def _self_check() -> None:
    try:
        db.verify_connection()
    except Exception as exc:
        print(f"MCP Server startup self-check failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def main() -> None:
    _self_check()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
