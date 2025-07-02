"""
Tools for interacting with Panther users.
"""

import logging
from typing import Annotated, Any, Dict

from pydantic import Field

from ..client import _execute_query, get_rest_client
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


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.USER_READ),
    }
)
async def get_user_by_id(
    user_id: Annotated[
        str,
        Field(
            description="The ID of the user to fetch",
            examples=["user-123"],
        ),
    ],
) -> Dict[str, Any]:
    """Get detailed information about a Panther user by ID

    Returns complete user information including email, names, role, authentication status, and timestamps.
    """
    logger.info(f"Fetching user details for user ID: {user_id}")

    try:
        async with get_rest_client() as client:
            # Allow 404 as a valid response to handle not found case
            result, status = await client.get(
                f"/users/{user_id}", expected_codes=[200, 404]
            )

            if status == 404:
                logger.warning(f"No user found with ID: {user_id}")
                return {
                    "success": False,
                    "message": f"No user found with ID: {user_id}",
                }

        logger.info(f"Successfully retrieved user details for user ID: {user_id}")
        return {"success": True, "user": result}
    except Exception as e:
        logger.error(f"Failed to get user details: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to get user details: {str(e)}",
        }
