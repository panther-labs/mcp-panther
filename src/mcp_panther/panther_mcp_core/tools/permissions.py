import logging
from typing import Any, Dict

from ..client import _execute_query
from ..permissions import requires_permissions, Permission, convert_permissions
from ..queries import LIST_USERS_QUERY
from ..client import get_rest_client
from .registry import mcp_tool

logger = logging.getLogger("mcp-panther")


@mcp_tool
async def get_permissions() -> Dict[str, Any]:
    """
    Use this tool to understand what permissions the user has.

    REQUIRED:
     - This tool should be ran if any 403 or forbidden errors are detected when calling other tools
    """

    logger.info("Getting permissions")
    try:
        async with get_rest_client() as client:
            result, _ = await client.get("/api-tokens/self")

        return {
            "success": True,
            "permissions": convert_permissions(result.get("permissions", [])),
        }
    except Exception as e:
        logger.error(f"Failed to fetch permissions: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch permissions: {str(e)}",
        }
