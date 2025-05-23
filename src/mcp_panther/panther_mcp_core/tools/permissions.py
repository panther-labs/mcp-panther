import logging
from typing import Any, Dict

from ..client import get_rest_client
from ..permissions import convert_permissions
from .registry import mcp_tool

logger = logging.getLogger("mcp-panther")


@mcp_tool
async def get_permissions() -> Dict[str, Any]:
    """
    Get the current user's permissions. Use this to diagnose permission errors and determine if a new API token is needed.
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
