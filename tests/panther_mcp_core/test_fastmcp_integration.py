import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("FASTMCP_INTEGRATION_TEST") != "1",
    reason="Integration test only runs when FASTMCP_INTEGRATION_TEST=1",
)

from fastmcp import Client

from src.mcp_panther.server import mcp


@pytest.mark.asyncio
async def test_tool_functionality():
    async with Client(mcp) as client:
        tools = await client.list_tools()

        for tool in tools:
            print(tool.name)
            print(tool.description)
            print(tool.inputSchema)
            print(tool.annotations)
            print("-" * 100)

        assert len(tools) > 0
