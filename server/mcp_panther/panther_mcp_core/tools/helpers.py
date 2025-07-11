"""
Tools for interacting with Panther's helpers.
"""

import logging
from typing import Any, Dict

from ..client import get_rest_client
from ..permissions import Permission, any_perms
from .registry import mcp_tool

logger = logging.getLogger("mcp-panther")


@mcp_tool(
    annotations={
        "permissions": any_perms(Permission.RULE_READ, Permission.POLICY_READ),
    }
)
async def get_global_helper_by_id(helper_id: str) -> Dict[str, Any]:
    """Get detailed information about a Panther global helper by ID

    Args:
        helper_id: The ID of the global helper to fetch

    Returns:
        Dict containing:
        - id: Global helper ID
        - body: Python code for the global helper
        - description: Description of the global helper
    """
    logger.info(f"Fetching global helper details for ID: {helper_id}")

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

        logger.info(f"Successfully retrieved global helper details for ID: {helper_id}")

        # Format the response
        return {"success": True, "global_helper": result}
    except Exception as e:
        logger.error(f"Failed to fetch global helper details: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch global helper details: {str(e)}",
        }


@mcp_tool(
    annotations={
        "permissions": any_perms(Permission.RULE_READ, Permission.POLICY_READ),
    }
)
async def list_global_helpers(
    cursor: str | None = None, limit: int = 100
) -> Dict[str, Any]:
    """List all global helpers from Panther with optional pagination

    Args:
        cursor: Optional cursor for pagination from a previous query
        limit: Optional maximum number of results to return (default: 100)
    """
    logger.info("Fetching global helpers from Panther")

    try:
        # Prepare query parameters
        params = {"limit": limit}
        if cursor and cursor.lower() != "null":  # Only add cursor if it's not null
            params["cursor"] = cursor
            logger.info(f"Using cursor for pagination: {cursor}")

        async with get_rest_client() as client:
            result, _ = await client.get("/globals", params=params)

        # Extract global helpers and pagination info
        global_helpers = result.get("results", [])
        next_cursor = result.get("next")

        logger.info(f"Successfully retrieved {len(global_helpers)} global helpers")

        # Format the response
        return {
            "success": True,
            "global_helpers": global_helpers,
            "total_global_helpers": len(global_helpers),
            "has_next_page": bool(next_cursor),
            "next_cursor": next_cursor,
        }
    except Exception as e:
        logger.error(f"Failed to fetch global helpers: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch global helpers: {str(e)}",
        }
