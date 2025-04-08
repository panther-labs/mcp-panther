"""
Tools for interacting with Panther's helpers.
"""
import logging
from typing import Any, Dict

import aiohttp

from ..client import get_panther_api_key, get_panther_rest_api_base
from .registry import mcp_tool

logger = logging.getLogger("mcp-panther")


@mcp_tool
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
        # Prepare headers
        headers = {
            "X-API-Key": get_panther_api_key(),
            "Content-Type": "application/json",
        }

        # Make the request
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{await get_panther_rest_api_base()}/globals/{helper_id}",
                headers=headers,
            ) as response:
                if response.status == 404:
                    logger.warning(f"No global helper found with ID: {helper_id}")
                    return {
                        "success": False,
                        "message": f"No global helper found with ID: {helper_id}",
                    }
                elif response.status != 200:
                    error_text = await response.text()
                    raise Exception(
                        f"Failed to fetch global helper details: {error_text}"
                    )

                global_helper_data = await response.json()

        logger.info(f"Successfully retrieved global helper details for ID: {helper_id}")

        # Format the response
        return {"success": True, "global_helper": global_helper_data}
    except Exception as e:
        logger.error(f"Failed to fetch global helper details: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch global helper details: {str(e)}",
        }


@mcp_tool
async def list_global_helpers(cursor: str = None, limit: int = 100) -> Dict[str, Any]:
    """List all global helpers from Panther with optional pagination

    Args:
        cursor: Optional cursor for pagination from a previous query
        limit: Optional maximum number of results to return (default: 100)
    """
    logger.info("Fetching global helpers from Panther")

    try:
        # Prepare headers
        headers = {
            "X-API-Key": get_panther_api_key(),
            "Content-Type": "application/json",
        }

        # Prepare query parameters
        params = {"limit": limit}
        if cursor and cursor.lower() != "null":  # Only add cursor if it's not null
            params["cursor"] = cursor
            logger.info(f"Using cursor for pagination: {cursor}")

        # Make the request
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{await get_panther_rest_api_base()}/globals",
                headers=headers,
                params=params,
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(
                        f"Failed to fetch global helpers (HTTP {response.status}): {error_text}"
                    )

                result = await response.json()

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
