"""
Tools for interacting with Panther roles.
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
async def list_roles(
    name_contains: Annotated[
        str | None,
        Field(
            description="Case-insensitive substring to search for within the role name",
            examples=["Admin", "Analyst", "Read"],
        ),
    ] = None,
    name: Annotated[
        str | None,
        Field(
            description="Exact match for a role's name. If provided, other parameters are ignored",
            examples=["Admin", "PantherReadOnly", "SecurityAnalyst"],
        ),
    ] = None,
    role_ids: Annotated[
        list[str],
        Field(
            description="List of specific role IDs to return",
            examples=[["Admin", "PantherReadOnly"], ["SecurityAnalyst"]],
        ),
    ] = [],
    sort_dir: Annotated[
        str | None,
        Field(
            description="Sort direction for the results",
            examples=["asc", "desc"],
        ),
    ] = "asc",
) -> dict[str, Any]:
    """List all roles from your Panther instance.

    Returns list of roles with metadata including permissions and settings.
    """
    logger.info("Fetching roles from Panther")

    try:
        # Prepare query parameters based on API spec
        params = {}
        if name_contains:
            params["name-contains"] = name_contains
        if name:
            params["name"] = name
        if role_ids:
            # Convert list to comma-delimited string as per API spec
            params["ids"] = ",".join(role_ids)
        if sort_dir:
            params["sort-dir"] = sort_dir

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
                "permissions": role.get("permissions"),
                "logTypeAccess": role.get("logTypeAccess"),
                "logTypeAccessKind": role.get("logTypeAccessKind"),
                "createdAt": role.get("createdAt"),
                "updatedAt": role.get("updatedAt"),
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
        "readOnlyHint": True,
    }
)
async def get_role(
    role_id: Annotated[
        str,
        Field(
            description="The ID of the role to fetch",
            examples=["Admin"],
        ),
    ],
) -> dict[str, Any]:
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
