"""
Tools for interacting with Panther users.
"""

import logging
from typing import Annotated, Any

from pydantic import Field

from ..client import get_rest_client
from ..permissions import Permission, all_perms
from .registry import mcp_tool

logger = logging.getLogger("mcp-panther")


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.USER_READ),
        "readOnlyHint": True,
    }
)
async def list_users(
    cursor: Annotated[
        str | None,
        Field(description="Optional cursor for pagination from a previous query"),
    ] = None,
    limit: Annotated[
        int,
        Field(
            description="Maximum number of results to return (1-60)",
            ge=1,
            le=60,
        ),
    ] = 60,
) -> dict[str, Any]:
    """List all Panther user accounts.

    Returns:
        Dict containing:
        - success: Boolean indicating if the query was successful
        - users: List of user accounts if successful
        - total_users: Number of users returned
        - has_next_page: Boolean indicating if more results are available
        - next_cursor: Cursor for fetching the next page of results
        - message: Error message if unsuccessful
    """
    logger.info("Fetching Panther users")

    try:
        # Use REST API with pagination support
        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor

        async with get_rest_client() as client:
            result, status = await client.get(
                "/users", params=params, expected_codes=[200]
            )

        if status != 200:
            raise Exception(f"API request failed with status {status}")

        users = result.get("results", [])
        next_cursor = result.get("next")

        logger.info(f"Successfully retrieved {len(users)} users")

        return {
            "success": True,
            "users": users,
            "total_users": len(users),
            "has_next_page": next_cursor is not None,
            "next_cursor": next_cursor,
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
        "readOnlyHint": True,
    }
)
async def get_user(
    user_id: Annotated[
        str,
        Field(
            description="The ID of the user to fetch",
            examples=["user-123", "john.doe@company.com", "<admin@example.com>"],
        ),
    ],
) -> dict[str, Any]:
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
