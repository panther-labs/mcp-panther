import logging
import sys

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

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

# Support multiple import paths to accommodate different execution contexts:
# 1. When running as a binary, uvx expects relative imports
# 2. When running with MCP inspector: `uv run mcp dev src/mcp_panther/server.py`
# 3. When installing: `uv run mcp install src/mcp_panther/server.py`
try:
    # Import MCP registries
    from panther_mcp_core.prompts.registry import register_all_prompts
    from panther_mcp_core.resources.registry import register_all_resources
    from panther_mcp_core.tools.registry import register_all_tools
except ImportError:
    # Import MCP registries
    from .panther_mcp_core.prompts.registry import register_all_prompts
    from .panther_mcp_core.resources.registry import register_all_resources
    from .panther_mcp_core.tools.registry import register_all_tools


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
