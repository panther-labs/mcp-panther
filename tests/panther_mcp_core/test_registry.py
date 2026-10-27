import pytest
from fastmcp import Client, FastMCP

import mcp_panther.panther_mcp_core.tools  # noqa: F401  # registers tools
from mcp_panther.panther_mcp_core.tools.registry import register_all_tools


async def _result_size_meta():
    mcp = FastMCP("test")
    register_all_tools(mcp)
    async with Client(mcp) as client:
        tools = await client.list_tools()
    assert tools
    return {(tool.meta or {}).get("anthropic/maxResultSizeChars") for tool in tools}


@pytest.mark.asyncio
async def test_result_size_meta_is_advertised_when_configured(monkeypatch):
    monkeypatch.setenv("MCP_MAX_RESULT_SIZE_CHARS", "200000")
    assert await _result_size_meta() == {200000}


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [None, "", "0", "-1", "large"])
async def test_result_size_meta_is_omitted_when_unset_or_invalid(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("MCP_MAX_RESULT_SIZE_CHARS", raising=False)
    else:
        monkeypatch.setenv("MCP_MAX_RESULT_SIZE_CHARS", value)
    assert await _result_size_meta() == {None}
