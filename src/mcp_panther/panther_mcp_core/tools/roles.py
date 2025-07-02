"""
Tools for interacting with Panther roles.
"""

import logging
from typing import Annotated, Any, Dict

from pydantic import Field

from ..client import get_rest_client
from ..permissions import Permission, all_perms
from .registry import mcp_tool

logger = logging.getLogger("mcp-panther")


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.USER_READ),
    }
)
async def list_roles(
    cursor: Annotated[
        str | None,
        Field(description="Optional cursor for pagination from a previous query"),
    ] = None,
    limit: Annotated[
        int,
        Field(
            description="Optional maximum number of results to return",
            ge=1,
            le=1000,
        ),
    ] = 100,
) -> Dict[str, Any]:
    """List all roles from your Panther instance.

    Returns paginated list of roles with metadata including permissions and settings.
    """
    logger.info(f"Fetching {limit} roles from Panther")

    try:
        # Prepare query parameters
        params = {"limit": limit}
        if cursor and cursor.lower() != "null":  # Only add cursor if it's not null
            params["cursor"] = cursor
            logger.info(f"Using cursor for pagination: {cursor}")

        async with get_rest_client() as client:
            result, _ = await client.get("/roles", params=params)

        # Extract roles and pagination info
        roles = result.get("results", [])
        next_cursor = result.get("next")

        # Keep only specific fields for each role to limit the amount of data returned
        filtered_roles_metadata = [
            {
                "id": role["id"],
                "name": role.get("name"),
                "description": role.get("description"),
                "permissions": role.get("permissions"),
                "managed": role.get("managed"),
                "createdAt": role.get("createdAt"),
                "lastModified": role.get("lastModified"),
            }
            for role in roles
        ]

        logger.info(f"Successfully retrieved {len(filtered_roles_metadata)} roles")

        return {
            "success": True,
            "roles": filtered_roles_metadata,
            "total_roles": len(filtered_roles_metadata),
            "has_next_page": bool(next_cursor),
            "next_cursor": next_cursor,
        }
    except Exception as e:
        logger.error(f"Failed to list roles: {str(e)}")
        return {"success": False, "message": f"Failed to list roles: {str(e)}"}


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.USER_READ),
    }
)
async def get_role_by_id(
    role_id: Annotated[
        str,
        Field(
            description="The ID of the role to fetch",
            examples=["Admin"],
        ),
    ],
) -> Dict[str, Any]:
    """Get detailed information about a Panther role by ID

    Returns complete role information including all permissions and settings.
    """
    logger.info(f"Fetching role details for role ID: {role_id}")

    try:
        async with get_rest_client() as client:
            # Allow 404 as a valid response to handle not found case
            result, status = await client.get(
                f"/roles/{role_id}", expected_codes=[200, 404]
            )

            if status == 404:
                logger.warning(f"No role found with ID: {role_id}")
                return {
                    "success": False,
                    "message": f"No role found with ID: {role_id}",
                }

        logger.info(f"Successfully retrieved role details for role ID: {role_id}")
        return {"success": True, "role": result}
    except Exception as e:
        logger.error(f"Failed to get role details: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to get role details: {str(e)}",
        }
