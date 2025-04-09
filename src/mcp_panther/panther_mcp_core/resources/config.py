"""
Resources for providing configuration information about the Panther MCP server.
"""

from typing import Any, Dict

from ..client import get_panther_gql_endpoint, get_panther_rest_api_base
from ..prompts.registry import get_available_prompt_names
from ..tools.registry import get_available_tool_names
from .registry import get_available_resource_paths, mcp_resource


@mcp_resource("config://panther")
async def get_panther_config() -> Dict[str, Any]:
    """Get the Panther configuration."""
    return {
        "gql_api_url": await get_panther_gql_endpoint(),
        "rest_api_url": await get_panther_rest_api_base(),
        "available_tools": get_available_tool_names(),
        "available_resources": get_available_resource_paths(),
        "available_prompts": get_available_prompt_names(),
    }
