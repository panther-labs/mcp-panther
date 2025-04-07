import logging
import sys

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.server import stdio
from mcp.server.lowlevel.server import Server

# Load environment variables from .env file if it exists
load_dotenv()


# Server name
MCP_SERVER_NAME = "mcp-panther"

# Configure logging with more detail
logging.basicConfig(
    level=logging.DEBUG,  # Change to DEBUG for more info
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,  # Ensure logs go to stderr
)
logger = logging.getLogger(MCP_SERVER_NAME)

# Import MCP registries
from panther_mcp_core.tools.registry import register_all_tools
from panther_mcp_core.prompts.registry import register_all_prompts
from panther_mcp_core.resources.registry import register_all_resources



# Server dependencies
deps = [
    "python-dotenv",
    "gql[aiohttp]",
    "aiohttp",
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


async def main():
    """Main entry point for the MCP server."""
    try:
        logger.info("Starting Panther MCP server...")
        server = Server(mcp)
        async with stdio.stdio_server() as (read_stream, write_stream):
            logger.info("Server running with stdio transport")
            await server.run(
                read_stream,
                write_stream,
                initialization_options={"name": MCP_SERVER_NAME},
            )
    except Exception as e:
        logger.error(f"Server error: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    try:
        import asyncio

        logger.info("Starting server from command line...")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)
