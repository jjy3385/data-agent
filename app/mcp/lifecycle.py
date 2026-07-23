import asyncio
import os
import sys
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.mcp.client_manager import MCPClientManager, MCPStartupError
from app.mcp.contracts import verify_tool_contracts

MCP_STARTUP_TIMEOUT_SECONDS = 30

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@asynccontextmanager
async def mcp_lifespan() -> AsyncIterator[MCPClientManager]:
    """단일 MCP Server 하위 프로세스를 시작하고 Tool Discovery·Contract 검증까지 마친 뒤
    장수명 MCPClientManager를 제공한다. 실패하면 이미 연 자원을 정리하고 Fail Closed 한다."""
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_server.server"],
        cwd=str(_REPO_ROOT),
        env=dict(os.environ),
    )

    async with AsyncExitStack() as stack:
        try:
            read_stream, write_stream = await stack.enter_async_context(stdio_client(server_params))
            session = await stack.enter_async_context(ClientSession(read_stream, write_stream))

            try:
                async with asyncio.timeout(MCP_STARTUP_TIMEOUT_SECONDS):
                    await session.initialize()
                    tools_result = await session.list_tools()
            except TimeoutError as exc:
                raise MCPStartupError(
                    f"MCP server did not become ready within {MCP_STARTUP_TIMEOUT_SECONDS}s",
                    reason="startup_timeout",
                ) from exc

            verify_tool_contracts(tools_result.tools)
        except MCPStartupError:
            raise
        except Exception as exc:
            raise MCPStartupError(f"Failed to start MCP server: {exc}", reason="startup_failed") from exc

        yield MCPClientManager(session)
