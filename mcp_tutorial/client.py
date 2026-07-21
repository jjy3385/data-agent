import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_path = Path(__file__).resolve().parent / "server.py"


async def main() -> None:
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_path)],
    )

    async with stdio_client(server_params) as streams:
        read_stream, write_stream = streams

        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            response = await session.list_tools()

            print("connected tools:")

            for tool in response.tools:
                print(f"- {tool.name}: {tool.description}")

            result = await session.call_tool(
                "get_product_by_id",
                arguments={"product_id": 707},
            )

            print("tool result:")

            for content in result.content:
                print(content)


if __name__ == "__main__":
    asyncio.run(main())
