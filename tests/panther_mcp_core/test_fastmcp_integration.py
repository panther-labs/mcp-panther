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
