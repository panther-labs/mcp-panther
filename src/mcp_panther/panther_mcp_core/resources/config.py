"""
Resources for providing configuration information about the Panther MCP server.
"""

from typing import Dict, Any
from ..client import PANTHER_GQL_API_URL, PANTHER_REST_API_URL
from ..tools.registry import get_available_tool_names
from ..prompts.registry import get_available_prompt_names
from .registry import mcp_resource, get_available_resource_paths


@mcp_resource("config://panther")
def get_panther_config() -> Dict[str, Any]:
    """Get the Panther configuration."""
    return {
        "gql_api_url": PANTHER_GQL_API_URL,
        "rest_api_url": PANTHER_REST_API_URL,
        "available_tools": get_available_tool_names(),
        "available_resources": get_available_resource_paths(),
        "available_prompts": get_available_prompt_names(),
    }
