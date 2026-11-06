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


@pytest.mark.asyncio
async def test_data_lake_tools_advertise_backend_specific_sql():
    """Clients need dialect and database guidance in the actual MCP metadata."""
    mcp = FastMCP("test")
    register_all_tools(mcp)
    async with Client(mcp) as client:
        tools = {tool.name: tool for tool in await client.list_tools()}

    query = tools["query_data_lake"]
    sql_description = query.inputSchema["properties"]["sql"]["description"]
    assert "Snowflake" in sql_description
    assert "Databricks" in sql_description
    database = query.inputSchema["properties"]["database_name"]
    assert database["default"] == "panther_logs.public"
    assert database["examples"] == ["panther_logs.public", "panther_logs"]
    assert "list_databases" in database["description"]
    assert "Databricks" in query.description
    assert "panther_logs.aws_cloudtrail" in query.description
    assert "ARRAY_CONTAINS(p_any_emails, 'user@domain.com')" in query.description
    assert "panther_logs.public.aws_cloudtrail" in query.description
    assert "'user@domain.com'::VARIANT" in query.description
    assert "Before using vendor-specific fields" in query.description
    assert "schemas already fetched in this conversation" in query.description
    assert "LIMIT 100" in query.description
    assert "max_rows only controls page size" in query.description
    assert "panther_signals.public.correlation_signals_variant" in query.description
    assert "data:field" in query.description
    assert "panther_signals.correlation_signals" in query.description
    assert "event:field::string = 'value'" in query.description
    assert "not regular structured log columns" in query.description
    assert "Databricks" in tools["get_table_schema"].description
    assert "Databricks" in tools["get_alert_event_stats"].description
