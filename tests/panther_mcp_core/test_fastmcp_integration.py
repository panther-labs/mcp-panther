import os

import pytest
from fastmcp.exceptions import ToolError

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
        for tool in [t for t in tools if "metrics" in t.name]:
            print(tool.name)
            print(tool.description)
            print(tool.inputSchema)
            print(tool.annotations)
            print("-" * 100)
        assert len(tools) > 0


@pytest.mark.asyncio
async def test_severity_alert_metrics_invalid_params():
    """Test that severity alert metrics properly validates parameters."""
    async with Client(mcp) as client:
        # Test invalid interval
        with pytest.raises(ToolError):
            await client.call_tool(
                "get_severity_alert_metrics",
                {"interval_in_minutes": 45},  # Invalid interval
            )

        # Test invalid alert type
        with pytest.raises(ToolError):
            await client.call_tool(
                "get_severity_alert_metrics", {"alert_types": ["INVALID_TYPE"]}
            )

        # Test invalid severity
        with pytest.raises(ToolError):
            await client.call_tool(
                "get_severity_alert_metrics", {"severities": ["INVALID_SEVERITY"]}
            )


@pytest.mark.asyncio
async def test_rule_alert_metrics_invalid_interval():
    """Test that rule alert metrics properly validates interval parameter."""
    async with Client(mcp) as client:
        with pytest.raises(ToolError) as exc_info:
            await client.call_tool(
                "get_rule_alert_metrics",
                {"interval_in_minutes": 45},  # Invalid interval
            )
        assert "Error calling tool 'get_rule_alert_metrics'" in str(exc_info.value)


@pytest.mark.asyncio
async def test_rule_alert_metrics_invalid_rule_ids():
    """Test that rule alert metrics properly validates rule ID formats."""
    async with Client(mcp) as client:
        # Test invalid rule ID format with @ symbol
        with pytest.raises(ToolError) as exc_info:
            await client.call_tool(
                "get_rule_alert_metrics",
                {"rule_ids": ["invalid@rule.id"]},  # Invalid rule ID format
            )
        assert "Error calling tool 'get_rule_alert_metrics'" in str(exc_info.value)

        # Test invalid rule ID format with spaces
        with pytest.raises(ToolError) as exc_info:
            await client.call_tool(
                "get_rule_alert_metrics",
                {"rule_ids": ["AWS CloudTrail"]},  # Invalid rule ID format with spaces
            )
        assert "Error calling tool 'get_rule_alert_metrics'" in str(exc_info.value)

        # Test invalid rule ID format with special characters
        with pytest.raises(ToolError) as exc_info:
            await client.call_tool(
                "get_rule_alert_metrics",
                {
                    "rule_ids": ["AWS#CloudTrail"]
                },  # Invalid rule ID format with special chars
            )
        assert "Error calling tool 'get_rule_alert_metrics'" in str(exc_info.value)
