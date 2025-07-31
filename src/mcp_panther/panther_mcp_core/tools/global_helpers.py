"""
Tools for interacting with Panther global helpers.
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
        "permissions": all_perms(Permission.RULE_READ),
        "readOnlyHint": True,
    }
)
async def list_global_helpers(
    cursor: Annotated[
        str | None,
        Field(description="Optional cursor for pagination from a previous query"),
    ] = None,
    limit: Annotated[
        int,
        Field(
            description="Maximum number of results to return (1-1000)",
            examples=[100, 25, 50],
            ge=1,
            le=1000,
        ),
    ] = 100,
    name_contains: Annotated[
        str | None,
        Field(
            description="Case-insensitive substring to search for in the global's name",
            examples=["aws", "crowdstrike", "utility"],
        ),
    ] = None,
    created_by: Annotated[
        str | None,
        Field(
            description="Filter by creator user ID or actor ID",
            examples=["user-123", "john.doe@company.com"],
        ),
    ] = None,
    last_modified_by: Annotated[
        str | None,
        Field(
            description="Filter by last modifier user ID or actor ID",
            examples=["user-456", "jane.smith@company.com"],
        ),
    ] = None,
) -> dict[str, Any]:
    """List all global helpers from your Panther instance. Global helpers are shared Python functions that can be used across multiple rules, policies, and other detections.

    Returns paginated list of global helpers with metadata including descriptions and code.
    """
    logger.info(f"Fetching {limit} global helpers from Panther")

    try:
        # Prepare query parameters based on API spec
        params = {"limit": limit}
        if cursor and cursor.lower() != "null":  # Only add cursor if it's not null
            params["cursor"] = cursor
            logger.info(f"Using cursor for pagination: {cursor}")
        if name_contains:
            params["name-contains"] = name_contains
        if created_by:
            params["created-by"] = created_by
        if last_modified_by:
            params["last-modified-by"] = last_modified_by

        async with get_rest_client() as client:
            result, _ = await client.get("/globals", params=params)

        # Extract globals and pagination info
        globals_list = result.get("results", [])
        next_cursor = result.get("next")

        # Keep only specific fields for each global helper to limit the amount of data returned
        filtered_globals_metadata = [
            {
                "id": global_helper["id"],
                "description": global_helper.get("description"),
                "tags": global_helper.get("tags"),
                "createdAt": global_helper.get("createdAt"),
                "lastModified": global_helper.get("lastModified"),
            }
            for global_helper in globals_list
        ]

        logger.info(
            f"Successfully retrieved {len(filtered_globals_metadata)} global helpers"
        )

        return {
            "success": True,
            "global_helpers": filtered_globals_metadata,
            "total_global_helpers": len(filtered_globals_metadata),
            "has_next_page": bool(next_cursor),
            "next_cursor": next_cursor,
        }
    except Exception as e:
        logger.error(f"Failed to list global helpers: {str(e)}")
        return {"success": False, "message": f"Failed to list global helpers: {str(e)}"}


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.RULE_READ),
        "readOnlyHint": True,
    }
)
async def get_global_helper(
    helper_id: Annotated[
        str,
        Field(
            description="The ID of the global helper to fetch",
            examples=["MyGlobalHelper", "AWSUtilities", "CrowdStrikeHelpers"],
        ),
    ],
) -> dict[str, Any]:
    """Get detailed information about a Panther global helper by ID

    Returns complete global helper information including Python body code and usage details.
    """
    logger.info(f"Fetching global helper details for helper ID: {helper_id}")

    try:
        async with get_rest_client() as client:
            # Allow 404 as a valid response to handle not found case
            result, status = await client.get(
                f"/globals/{helper_id}", expected_codes=[200, 404]
            )

            if status == 404:
                logger.warning(f"No global helper found with ID: {helper_id}")
                return {
                    "success": False,
                    "message": f"No global helper found with ID: {helper_id}",
                }

        logger.info(
            f"Successfully retrieved global helper details for helper ID: {helper_id}"
        )
        return {"success": True, "global_helper": result}
    except Exception as e:
        logger.error(f"Failed to get global helper details: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to get global helper details: {str(e)}",
        }
