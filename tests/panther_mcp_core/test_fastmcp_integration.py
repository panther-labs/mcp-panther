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
        for tool in [t for t in tools if "list_detections" in t.name]:
            print(f"Tool: {tool.name}")
            print(f"Description: {tool.description}")
            print(f"Input Schema: {tool.inputSchema}")
            print(f"Annotations: {tool.annotations}")
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
        # FastMCP 2.10+ provides more specific validation error messages
        error_msg = str(exc_info.value)
        assert (
            "Input validation error" in error_msg
            or "Error calling tool 'get_rule_alert_metrics'" in error_msg
        )


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
        # FastMCP 2.10+ provides more specific validation error messages
        error_msg = str(exc_info.value)
        assert (
            "Input validation error" in error_msg
            or "Error calling tool 'get_rule_alert_metrics'" in error_msg
        )

        # Test invalid rule ID format with spaces
        with pytest.raises(ToolError) as exc_info:
            await client.call_tool(
                "get_rule_alert_metrics",
                {"rule_ids": ["AWS CloudTrail"]},  # Invalid rule ID format with spaces
            )
        # FastMCP 2.10+ provides more specific validation error messages
        error_msg = str(exc_info.value)
        assert (
            "Input validation error" in error_msg
            or "Error calling tool 'get_rule_alert_metrics'" in error_msg
        )

        # Test invalid rule ID format with special characters
        with pytest.raises(ToolError) as exc_info:
            await client.call_tool(
                "get_rule_alert_metrics",
                {
                    "rule_ids": ["AWS#CloudTrail"]
                },  # Invalid rule ID format with special chars
            )
        # FastMCP 2.10+ provides more specific validation error messages
        error_msg = str(exc_info.value)
        assert (
            "Input validation error" in error_msg
            or "Error calling tool 'get_rule_alert_metrics'" in error_msg
        )


@pytest.mark.asyncio
async def test_get_scheduled_query_uuid_validation_tool():
    """Test that get_scheduled_query only accepts valid UUIDs for query_id at the tool interface level."""
    from fastmcp import Client
    from fastmcp.exceptions import ToolError

    from src.mcp_panther.server import mcp

    async with Client(mcp) as client:
        # Valid UUID should work (should not raise)
        valid_uuid = "6c6574cb-fbf9-49fc-baad-1a99464ef09e"
        try:
            await client.call_tool("get_scheduled_query", {"query_id": valid_uuid})
        except ToolError as e:
            # If the query doesn't exist, that's fine, as long as it's not a validation error
            assert "validation error" not in str(e)

        # Invalid UUID should raise a ToolError
        with pytest.raises(ToolError) as exc_info:
            await client.call_tool("get_scheduled_query", {"query_id": "not-a-uuid"})
        error_msg = str(exc_info.value)
        assert "validation error" in error_msg


# Test constants
TEST_HOST = "127.0.0.1"
TEST_PORT = 3001
TEST_TIMEOUT = 5.0
STARTUP_DELAY = 2.0


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
            mcp.run(transport="streamable-http", host=TEST_HOST, port=TEST_PORT)
        except Exception as e:
            server_error = e
            print(f"Server error: {e}")
        finally:
            server_started.set()

    # Start server in background thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Give server time to start
    await asyncio.sleep(STARTUP_DELAY)

    # Check if server had startup errors
    if server_error:
        pytest.fail(f"Server failed to start: {server_error}")

    try:
        # Try basic HTTP connectivity first - any response means server is active
        async with httpx.AsyncClient() as http_client:
            try:
                response = await http_client.get(
                    f"http://{TEST_HOST}:{TEST_PORT}/", timeout=TEST_TIMEOUT
                )
                print(f"HTTP response status: {response.status_code}")
                # Any response means the server is running
            except Exception as e:
                pytest.fail(f"Server not responding on port {TEST_PORT}: {e}")

        # Test MCP client connection over HTTP (use trailing slash to avoid redirects)
        async with Client(f"http://{TEST_HOST}:{TEST_PORT}/mcp/") as client:
            # Test basic tool listing
            tools = await client.list_tools()
            assert len(tools) > 0

            # Test tool execution over streaming HTTP
            metrics_tools = [t for t in tools if "metrics" in t.name]
            assert len(metrics_tools) > 0

    except Exception as e:
        pytest.fail(f"Test failed: {e}")

    # Server will be cleaned up when thread exits
