"""
Tools for interacting with Panther users.
"""

import logging
from typing import Any, Dict

from ..client import _execute_query
from ..permissions import Permission, all_perms
from ..queries import LIST_USERS_QUERY
from .registry import mcp_tool

logger = logging.getLogger("mcp-panther")


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.USER_READ),
    }
)
async def list_panther_users() -> Dict[str, Any]:
    """List all Panther user accounts.

    Returns:
        Dict containing:
        - success: Boolean indicating if the query was successful
        - users: List of user accounts if successful
        - message: Error message if unsuccessful
    """
    logger.info("Fetching all Panther users")

    try:
        # Execute query
        result = await _execute_query(LIST_USERS_QUERY, {})

        if not result or "users" not in result:
            raise Exception("Failed to fetch users")

        users = result["users"]

        logger.info(f"Successfully retrieved {len(users)} users")

        return {
            "success": True,
            "users": users,
        }

    except Exception as e:
        logger.error(f"Failed to fetch users: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch users: {str(e)}",
        }
