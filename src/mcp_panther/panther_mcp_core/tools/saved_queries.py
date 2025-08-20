"""
Tools for managing Panther saved queries.

This module provides functionality for:
- Creating saved queries: SQL queries saved for on-demand execution by LLMs and analysts
- Listing saved queries: View all saved queries (both scheduled and on-demand)
- Retrieving saved queries: Get full details including SQL content for specific queries

Saved queries can be used for security analysis, reporting, and monitoring purposes.
Both scheduled (automated) and on-demand queries are managed through this interface.
"""

import logging
from typing import Annotated, Any, Dict
from uuid import UUID

from pydantic import BeforeValidator, Field

from ..client import get_rest_client
from ..permissions import Permission, all_perms
from ..utils.sql_validation import validate_sql_comprehensive
from .registry import mcp_tool

logger = logging.getLogger("mcp-panther")


def _validate_query_name(v: str) -> str:
    """Validate query name is not empty after stripping."""
    if not v or not v.strip():
        raise ValueError("Query name cannot be empty")
    return v.strip()


def _validate_sql_query(v: str) -> str:
    """Validate SQL query using shared validation utility."""
    if not v or not v.strip():
        raise ValueError("SQL query cannot be empty")

    # Use comprehensive validation for saved queries
    # Always require time filter and enforce read-only operations
    sql_validation = validate_sql_comprehensive(
        sql=v.strip(),
        require_time_filter=True,
        read_only=True,
        database_name=None,  # Will be validated at query execution time
    )
    if not sql_validation["valid"]:
        raise ValueError(sql_validation["error"])

    # Return the processed SQL with reserved words handled
    return sql_validation.get("processed_sql", v.strip())


def _validate_description(v: str | None) -> str | None:
    """Strip description if provided."""
    return v.strip() if v else None


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.DATA_ANALYTICS_MODIFY),
        "readOnlyHint": False,
    }
)
async def create_saved_query(
    name: Annotated[
        str,
        BeforeValidator(_validate_query_name),
        Field(
            description="Name for the saved query",
            examples=[
                "Failed Login Analysis",
                "Weekly Security Report",
                "Suspicious S3 Activity",
            ],
        ),
    ],
    sql: Annotated[
        str,
        BeforeValidator(_validate_sql_query),
        Field(
            description="The SQL query to save. Must include a p_event_time filter for performance.",
            examples=[
                "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_occurs_since('1 d') AND errorcode IS NOT NULL",
                "SELECT sourceipaddress, COUNT(*) FROM panther_logs.public.aws_cloudtrail WHERE p_occurs_since('6 h') GROUP BY sourceipaddress",
            ],
        ),
    ],
    description: Annotated[
        str | None,
        BeforeValidator(_validate_description),
        Field(
            description="Optional description of what the query accomplishes",
            examples=[
                "Analyze failed login attempts from the last day",
                "Summary of IP activity over the last 6 hours",
            ],
        ),
    ] = None,
    enabled: Annotated[
        bool,
        Field(
            description="Whether to enable the query to run on a schedule (default: False for on-demand queries)"
        ),
    ] = False,
    cron_expression: Annotated[
        str | None,
        Field(
            description="Cron expression for scheduled queries (e.g., '0 9 * * 1' for Mondays at 9 AM)",
            examples=["0 9 * * 1", "0 */6 * * *", "0 0 * * 0"],
        ),
    ] = None,
    timeout_minutes: Annotated[
        int,
        Field(description="Query timeout in minutes (default: 30)", ge=1, le=300),
    ] = 30,
) -> Dict[str, Any]:
    """Create a saved query that can be executed on-demand or on a schedule.

    This tool allows you to persist SQL queries for later use, making it easy to
    recall and re-run common analysis queries without having to reconstruct them.
    Queries can be saved as on-demand (enabled=False) or scheduled (enabled=True).
    Saved queries can be retrieved using list_saved_queries() and executed
    using the query_data_lake tool.

    Args:
        name: A descriptive name for the saved query
        sql: The SQL query text to save (must include p_event_time filter)
        description: Optional description of what the query accomplishes
        enabled: Whether to enable the query to run on a schedule
        cron_expression: Cron expression for scheduled queries (required if enabled=True)
        timeout_minutes: Query timeout in minutes

    Returns:
        Dict containing:
        - success: Boolean indicating if the query was saved successfully
        - query_id: ID of the created query if successful
        - query: Created query information if successful
        - message: Success or error message if unsuccessful
    """
    logger.info(f"Creating saved query: {name} (enabled: {enabled})")

    try:
        # Additional validation for schedule parameters (BeforeValidator handles the rest)
        if enabled and not cron_expression:
            return {
                "success": False,
                "message": "cron_expression is required when enabled=True",
            }

        # Prepare the request payload (parameters are already validated by BeforeValidator)
        query_data = {
            "name": name,
            "sql": sql,
            "enabled": enabled,
        }

        if description:
            query_data["description"] = description

        # Add schedule configuration if enabled
        if enabled and cron_expression:
            query_data["schedule"] = {
                "cron": cron_expression,
                "disabled": False,
                "timeoutMinutes": timeout_minutes,
            }

        logger.debug(f"Creating query with data: {query_data}")

        # Execute the REST API call
        async with get_rest_client() as client:
            response_data, status_code = await client.post("/queries", json=query_data)

            if status_code < 200 or status_code >= 300:
                logger.error(f"API request failed with status {status_code}")
                return {
                    "success": False,
                    "message": f"API request failed with status {status_code}",
                }

        logger.info(
            f"Successfully created saved query: {name} with ID: {response_data.get('id')}"
        )

        # Format the response
        return {
            "success": True,
            "query_id": response_data.get("id"),
            "query": response_data,
            "message": f"Successfully created saved query '{name}'",
        }
    except Exception as e:
        logger.error(f"Failed to create saved query: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to create saved query: {str(e)}",
        }


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.DATA_ANALYTICS_READ),
        "readOnlyHint": True,
    }
)
async def list_saved_queries(
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
            description="Optional substring to filter saved queries by name (case-insensitive)"
        ),
    ] = None,
) -> Dict[str, Any]:
    """List all saved queries from your Panther instance.

    This includes both scheduled queries (that run automatically) and on-demand saved queries.
    Saved queries are SQL queries saved for recurring analysis, reporting, and monitoring tasks.

    Note: SQL content is excluded from list responses to prevent token limits.
    Use get_saved_query() to retrieve the full SQL for a specific query.

    Returns:
        Dict containing:
        - success: Boolean indicating if the query was successful
        - queries: List of saved queries if successful, each containing:
            - id: Query ID
            - name: Query name
            - description: Query description
            - enabled: Whether the query runs on a schedule
            - schedule: Schedule configuration (cron, rate, timeout) if enabled
            - managed: Whether the query is managed by Panther
            - createdAt: Creation timestamp
            - updatedAt: Last update timestamp
        - total_queries: Number of queries returned
        - has_next_page: Boolean indicating if more results are available
        - next_cursor: Cursor for fetching the next page of results
        - message: Error message if unsuccessful
    """
    logger.info("Listing saved queries")

    try:
        # Prepare query parameters
        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor

        logger.debug(f"Query parameters: {params}")

        # Execute the REST API call
        async with get_rest_client() as client:
            response_data, status_code = await client.get("/queries", params=params)

            if status_code < 200 or status_code >= 300:
                logger.error(f"API request failed with status {status_code}")
                return {
                    "success": False,
                    "message": f"Failed to list saved queries: API returned status {status_code}",
                }

        # Extract queries from response
        queries = response_data.get("results", [])
        next_cursor = response_data.get("next")

        # Remove SQL content to prevent token limit issues
        # Full SQL can be retrieved using get_saved_query
        for query in queries:
            if "sql" in query:
                del query["sql"]

        # Filter by name_contains if provided
        if name_contains:
            queries = [
                q for q in queries if name_contains.lower() in q.get("name", "").lower()
            ]

        logger.info(f"Successfully retrieved {len(queries)} saved queries")

        # Format the response
        return {
            "success": True,
            "queries": queries,
            "total_queries": len(queries),
            "has_next_page": bool(next_cursor),
            "next_cursor": next_cursor,
        }
    except Exception as e:
        logger.error(f"Failed to list saved queries: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to list saved queries: {str(e)}",
        }


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.DATA_ANALYTICS_READ),
        "readOnlyHint": True,
    }
)
async def get_saved_query(
    query_id: Annotated[
        UUID,
        Field(
            description="The ID of the saved query to fetch (must be a UUID)",
            examples=["6c6574cb-fbf9-49fc-baad-1a99464ef09e"],
        ),
    ],
) -> Dict[str, Any]:
    """Get detailed information about a specific saved query by ID.

    Returns complete saved query information including SQL, schedule configuration (if enabled),
    and metadata. This works for both scheduled and on-demand saved queries.

    Returns:
        Dict containing:
        - success: Boolean indicating if the query was successful
        - query: Saved query information if successful, containing:
            - id: Query ID
            - name: Query name
            - description: Query description
            - sql: The SQL query text
            - enabled: Whether the query runs on a schedule
            - schedule: Schedule configuration (cron, rate, timeout) if enabled
            - managed: Whether the query is managed by Panther
            - createdAt: Creation timestamp
            - updatedAt: Last update timestamp
        - message: Error message if unsuccessful
    """
    logger.info(f"Fetching saved query: {query_id}")

    try:
        # Execute the REST API call
        async with get_rest_client() as client:
            response_data, status_code = await client.get(f"/queries/{str(query_id)}")

            if status_code < 200 or status_code >= 300:
                logger.error(f"API request failed with status {status_code}")
                return {
                    "success": False,
                    "message": f"Failed to fetch saved query: API returned status {status_code}",
                }

        logger.info(f"Successfully retrieved saved query: {query_id}")

        # Format the response
        return {
            "success": True,
            "query": response_data,
        }
    except Exception as e:
        logger.error(f"Failed to fetch saved query: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch saved query: {str(e)}",
        }
