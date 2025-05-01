import asyncio
import logging
import os
import signal
import sys
import threading

import click
from fastmcp import FastMCP

# Server name
MCP_SERVER_NAME = "mcp-panther"

# Get log level from environment variable, default to DEBUG if not set
log_level_name = os.environ.get("LOG_LEVEL", "DEBUG")

# Convert string log level to logging constant
log_level = getattr(logging, log_level_name.upper(), logging.DEBUG)

# Configure logging with more detail
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(MCP_SERVER_NAME)

# Support multiple import paths to accommodate different execution contexts:
# 1. When running as a binary, uvx expects relative imports
# 2. When running with MCP inspector: `uv run mcp dev src/mcp_panther/server.py`
# 3. When installing: `uv run mcp install src/mcp_panther/server.py`
try:
    from panther_mcp_core.prompts.registry import register_all_prompts
    from panther_mcp_core.resources.registry import register_all_resources
    from panther_mcp_core.tools.registry import register_all_tools
except ImportError:
    from .panther_mcp_core.prompts.registry import register_all_prompts
    from .panther_mcp_core.resources.registry import register_all_resources
    from .panther_mcp_core.tools.registry import register_all_tools

# Server dependencies
deps = [
    "gql[aiohttp]",
    "aiohttp",
    "anyascii",
    "mcp[cli]",
]

# Create the MCP server
mcp = FastMCP(MCP_SERVER_NAME, dependencies=deps)

# Register all tools with MCP using the registry
register_all_tools(mcp)
# Register all prompts with MCP using the registry
register_all_prompts(mcp)
# Register all resources with MCP using the registry
register_all_resources(mcp)


def handle_signals():
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        os._exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGHUP, signal_handler)


@click.command()
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse"]),
    default=os.environ.get("MCP_TRANSPORT", default="stdio"),
    help="Transport type (stdio or sse)",
)
@click.option(
    "--port",
    default=int(os.environ.get("MCP_PORT", default="3000")),
    help="Port to use for SSE transport",
)
@click.option(
    "--host",
    default=os.environ.get("MCP_HOST", default="127.0.0.1"),
    help="Host to bind to for SSE transport",
)
def main(transport: str, port: int, host: str):
    handle_signals()

    if transport == "sse":
        ...
    else:
        logger.info("Starting Panther MCP Server with stdio transport")

        def run_mcp():
            try:
                mcp.run(transport=transport)
            except Exception as e:
                logger.error(f"MCP server error: {e}", exc_info=True)

        # Run MCP in a separate thread
        mcp_thread = threading.Thread(target=run_mcp)
        mcp_thread.start()

        async def wait_for_stdin_close():
            logger.debug("Waiting for EOF on stdin...")
            await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            logger.info("EOF on stdin detected, attempting graceful shutdown")
            # Best-effort cleanup: exit when thread stops
            sys.exit(0)

        try:
            asyncio.run(wait_for_stdin_close())
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, exiting.")
            sys.exit(0)
