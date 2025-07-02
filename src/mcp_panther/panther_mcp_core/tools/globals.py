"""
Tools for interacting with Panther global helpers.
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
        "permissions": all_perms(Permission.RULE_READ),
    }
)
async def list_globals(
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
    """List all global helpers from your Panther instance. Global helpers are shared Python functions that can be used across multiple rules, policies, and other detections.

    Returns paginated list of global helpers with metadata including descriptions and code.
    """
    logger.info(f"Fetching {limit} global helpers from Panther")

    try:
        # Prepare query parameters
        params = {"limit": limit}
        if cursor and cursor.lower() != "null":  # Only add cursor if it's not null
            params["cursor"] = cursor
            logger.info(f"Using cursor for pagination: {cursor}")

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
                "displayName": global_helper.get("displayName"),
                "enabled": global_helper.get("enabled"),
                "managed": global_helper.get("managed"),
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
            "globals": filtered_globals_metadata,
            "total_globals": len(filtered_globals_metadata),
            "has_next_page": bool(next_cursor),
            "next_cursor": next_cursor,
        }
    except Exception as e:
        logger.error(f"Failed to list global helpers: {str(e)}")
        return {"success": False, "message": f"Failed to list global helpers: {str(e)}"}


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.RULE_READ),
    }
)
async def get_global_by_id(
    global_id: Annotated[
        str,
        Field(
            description="The ID of the global helper to fetch",
            examples=["MyGlobalHelper"],
        ),
    ],
) -> Dict[str, Any]:
    """Get detailed information about a Panther global helper by ID

    Returns complete global helper information including Python body code and usage details.
    """
    logger.info(f"Fetching global helper details for global ID: {global_id}")

    try:
        async with get_rest_client() as client:
            # Allow 404 as a valid response to handle not found case
            result, status = await client.get(
                f"/globals/{global_id}", expected_codes=[200, 404]
            )

            if status == 404:
                logger.warning(f"No global helper found with ID: {global_id}")
                return {
                    "success": False,
                    "message": f"No global helper found with ID: {global_id}",
                }

        logger.info(
            f"Successfully retrieved global helper details for global ID: {global_id}"
        )
        return {"success": True, "global": result}
    except Exception as e:
        logger.error(f"Failed to get global helper details: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to get global helper details: {str(e)}",
        }
