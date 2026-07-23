from typing import Any

import anyio

from mcp_server import readonly_query_executor


async def execute_readonly_query(
    sql: str,
    parameters: list,
    correlation_id: str,
    query_timeout_seconds: int,
    maximum_returned_rows: int,
) -> dict[str, Any]:
    result = await anyio.to_thread.run_sync(
        readonly_query_executor.execute,
        sql,
        parameters,
        query_timeout_seconds,
        maximum_returned_rows,
    )
    result["correlation_id"] = correlation_id
    return result
