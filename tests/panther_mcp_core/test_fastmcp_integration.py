import asyncio
import os
import threading

import httpx
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


@pytest.mark.asyncio
async def test_streaming_http_transport():
    """Test streaming HTTP transport functionality."""

    # Flag to track server status
    server_started = threading.Event()
    server_error = None

    def run_server():
        nonlocal server_error
        try:
            from mcp_panther.server import mcp

            print("Starting server...")
            mcp.run(transport="streamable-http", host="127.0.0.1", port=3001)
        except Exception as e:
            server_error = e
            print(f"Server error: {e}")
        finally:
            server_started.set()

    # Start server in background thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Give server time to start
    await asyncio.sleep(2)

    # Check if server had startup errors
    if server_error:
        pytest.fail(f"Server failed to start: {server_error}")

    try:
        # Try basic HTTP connectivity first
        async with httpx.AsyncClient() as http_client:
            # Test if port is responding (404 is expected for root path)
            try:
                response = await http_client.get("http://127.0.0.1:3001/", timeout=5.0)
                print(f"HTTP response status: {response.status_code}")
                # 404 is expected - server only exposes MCP endpoint, not general web interface
                if response.status_code not in [200, 404]:
                    pytest.fail(f"Unexpected HTTP status: {response.status_code}")
            except Exception as e:
                pytest.fail(f"Server not responding on port 3001: {e}")

        # Test MCP client connection over HTTP (use trailing slash to avoid redirects)
        async with Client("http://127.0.0.1:3001/mcp/") as client:
            # Test basic tool listing
            tools = await client.list_tools()
            assert len(tools) > 0

            # Test tool execution over streaming HTTP
            metrics_tools = [t for t in tools if "metrics" in t.name]
            assert len(metrics_tools) > 0

    except Exception as e:
        pytest.fail(f"Test failed: {e}")

    # Server will be cleaned up when thread exits
