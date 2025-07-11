"""
Tools for interacting with Panther log sources.
"""

import logging
from typing import Any, Dict, List

from ..client import _create_panther_client
from ..permissions import Permission, all_perms
from ..queries import GET_SOURCES_QUERY
from .registry import mcp_tool

logger = logging.getLogger("mcp-panther")


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.RULE_READ),
    }
)
async def list_log_sources(
    cursor: str | None = None,
    log_types: List[str] | None = None,
    is_healthy: bool | None = None,
    integration_type: str | None = None,
) -> Dict[str, Any]:
    """List log sources from Panther with optional filters.

    Args:
        cursor: Optional cursor for pagination from a previous query
        log_types: Optional list of log types to filter by
        is_healthy: Optional boolean to filter by health status
        integration_type: Optional integration type to filter by (e.g. "S3")
    """
    logger.info("Fetching log sources from Panther")

    try:
        client = await _create_panther_client()

        # Prepare input variables
        variables = {"input": {}}

        # Add cursor if provided
        if cursor:
            variables["input"]["cursor"] = cursor
            logger.info(f"Using cursor for pagination: {cursor}")

        logger.debug(f"Query variables: {variables}")

        # Execute the query asynchronously
        async with client as session:
            result = await session.execute(GET_SOURCES_QUERY, variable_values=variables)

        # Log the raw result for debugging
        logger.debug(f"Raw query result: {result}")

        # Process results
        sources_data = result.get("sources", {})
        source_edges = sources_data.get("edges", [])
        page_info = sources_data.get("pageInfo", {})

        # Extract sources from edges
        sources = [edge["node"] for edge in source_edges]

        # Apply post-request filtering
        if is_healthy is not None:
            sources = [
                source for source in sources if source["isHealthy"] == is_healthy
            ]
            logger.info(f"Filtered by health status: {is_healthy}")

        if log_types:
            sources = [
                source
                for source in sources
                if any(log_type in source["logTypes"] for log_type in log_types)
            ]
            logger.info(f"Filtered by log types: {log_types}")

        if integration_type:
            sources = [
                source
                for source in sources
                if source["integrationType"] == integration_type
            ]
            logger.info(f"Filtered by integration type: {integration_type}")

        logger.info(f"Successfully retrieved {len(sources)} log sources")

        # Format the response
        return {
            "success": True,
            "sources": sources,
            "total_sources": len(sources),
            "has_next_page": page_info.get("hasNextPage", False),
            "has_previous_page": page_info.get("hasPreviousPage", False),
            "end_cursor": page_info.get("endCursor"),
            "start_cursor": page_info.get("startCursor"),
        }
    except Exception as e:
        logger.error(f"Failed to fetch log sources: {str(e)}")
        return {"success": False, "message": f"Failed to fetch log sources: {str(e)}"}
