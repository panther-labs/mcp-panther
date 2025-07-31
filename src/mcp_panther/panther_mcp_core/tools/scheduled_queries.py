"""
Tools for managing Panther scheduled queries.

Scheduled queries are SQL queries that run on a schedule and can be used for
various analysis and reporting purposes.
"""

import logging
from typing import Annotated, Any, Dict
from uuid import UUID

from pydantic import Field

from ..client import get_rest_client
from ..permissions import Permission, all_perms
from .registry import mcp_tool

logger = logging.getLogger("mcp-panther")


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.DATA_ANALYTICS_READ),
        "readOnlyHint": True,
    }
)
async def list_scheduled_queries(
    cursor: Annotated[
        str | None,
        Field(description="Optional cursor for pagination from a previous query"),
    ] = None,
    limit: Annotated[
        int,
        Field(
            description="Maximum number of results to return (1-1000)",
            ge=1,
            le=1000,
        ),
    ] = 100,
    name_contains: Annotated[
        str | None,
        Field(
            description="Optional substring to filter scheduled queries by name (case-insensitive)"
        ),
    ] = None,
) -> Dict[str, Any]:
    """List all scheduled queries from your Panther instance.

    Scheduled queries are SQL queries that run automatically on a defined schedule
    for recurring analysis, reporting, and monitoring tasks.

    Note: SQL content is excluded from list responses to prevent token limits.
    Use get_scheduled_query() to retrieve the full SQL for a specific query.

    Returns:
        Dict containing:
        - success: Boolean indicating if the query was successful
        - queries: List of scheduled queries if successful, each containing:
            - id: Query ID
            - name: Query name
            - description: Query description
            - schedule: Schedule configuration (cron, rate, timeout)
            - managed: Whether the query is managed by Panther
            - createdAt: Creation timestamp
            - updatedAt: Last update timestamp
        - total_queries: Number of queries returned
        - has_next_page: Boolean indicating if more results are available
        - next_cursor: Cursor for fetching the next page of results
        - message: Error message if unsuccessful
    """
    logger.info("Listing scheduled queries")

    try:
        # Prepare query parameters
        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor

        logger.debug(f"Query parameters: {params}")

        # Execute the REST API call
        async with get_rest_client() as client:
            response_data, status_code = await client.get("/queries", params=params)

        # Extract queries from response
        queries = response_data.get("results", [])
        next_cursor = response_data.get("next")

        # Remove SQL content to prevent token limit issues
        # Full SQL can be retrieved using get_scheduled_query
        for query in queries:
            if "sql" in query:
                del query["sql"]

        # Filter by name_contains if provided
        if name_contains:
            queries = [
                q for q in queries if name_contains.lower() in q.get("name", "").lower()
            ]

        logger.info(f"Successfully retrieved {len(queries)} scheduled queries")

        # Format the response
        return {
            "success": True,
            "queries": queries,
            "total_queries": len(queries),
            "has_next_page": bool(next_cursor),
            "next_cursor": next_cursor,
        }
    except Exception as e:
        logger.error(f"Failed to list scheduled queries: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to list scheduled queries: {str(e)}",
        }


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.DATA_ANALYTICS_READ),
        "readOnlyHint": True,
    }
)
async def get_scheduled_query(
    query_id: Annotated[
        UUID,
        Field(
            description="The ID of the scheduled query to fetch (must be a UUID)",
            examples=["6c6574cb-fbf9-49fc-baad-1a99464ef09e"],
        ),
    ],
) -> Dict[str, Any]:
    """Get detailed information about a specific scheduled query by ID.

    Returns complete scheduled query information including SQL, schedule configuration,
    and metadata.

    Returns:
        Dict containing:
        - success: Boolean indicating if the query was successful
        - query: Scheduled query information if successful, containing:
            - id: Query ID
            - name: Query name
            - description: Query description
            - sql: The SQL query text
            - schedule: Schedule configuration (cron, rate, timeout)
            - managed: Whether the query is managed by Panther
            - createdAt: Creation timestamp
            - updatedAt: Last update timestamp
        - message: Error message if unsuccessful
    """
    logger.info(f"Fetching scheduled query: {query_id}")

    try:
        # Execute the REST API call
        async with get_rest_client() as client:
            response_data, status_code = await client.get(f"/queries/{str(query_id)}")

        logger.info(f"Successfully retrieved scheduled query: {query_id}")

        # Format the response
        return {
            "success": True,
            "query": response_data,
        }
    except Exception as e:
        logger.error(f"Failed to fetch scheduled query: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch scheduled query: {str(e)}",
        }
