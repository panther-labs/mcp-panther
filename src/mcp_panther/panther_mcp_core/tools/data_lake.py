"""
Tools for interacting with Panther's data lake.
"""

import asyncio
import logging
import re
import time
from enum import Enum
from typing import Annotated, Any, Dict, List

import sqlparse
from pydantic import Field

from ..client import _create_panther_client, _get_today_date_range
from ..permissions import Permission, all_perms
from ..queries import (
    CANCEL_DATA_LAKE_QUERY,
    EXECUTE_DATA_LAKE_QUERY,
    GET_COLUMNS_FOR_TABLE_QUERY,
    GET_DATA_LAKE_QUERY,
    LIST_DATABASES_QUERY,
    LIST_TABLES_QUERY,
)
from .registry import mcp_tool

logger = logging.getLogger("mcp-panther")

INITIAL_QUERY_SLEEP_SECONDS = 1
MAX_QUERY_SLEEP_SECONDS = 5


# Snowflake reserved words that should be quoted when used as identifiers
SNOWFLAKE_RESERVED_WORDS = {
    "SELECT",
    "FROM",
    "WHERE",
    "JOIN",
    "LEFT",
    "RIGHT",
    "INNER",
    "OUTER",
    "ON",
    "AS",
    "ORDER",
    "GROUP",
    "BY",
    "HAVING",
    "UNION",
    "ALL",
    "DISTINCT",
    "INSERT",
    "UPDATE",
    "DELETE",
    "CREATE",
    "ALTER",
    "DROP",
    "TABLE",
    "VIEW",
    "INDEX",
    "COLUMN",
    "PRIMARY",
    "KEY",
    "FOREIGN",
    "UNIQUE",
    "NOT",
    "NULL",
    "DEFAULT",
    "CHECK",
    "CONSTRAINT",
    "REFERENCES",
    "CASCADE",
    "RESTRICT",
    "SET",
    "VALUES",
    "INTO",
    "CASE",
    "WHEN",
    "THEN",
    "ELSE",
    "END",
    "IF",
    "EXISTS",
    "LIKE",
    "BETWEEN",
    "IN",
    "IS",
    "AND",
    "OR",
    "WITH",
}


def wrap_reserved_words(sql: str) -> str:
    """
    Simple function to wrap reserved words in SQL using sqlparse.

    This function:
    1. Parses the SQL using sqlparse
    2. Identifies string literals that match reserved words
    3. Converts single-quoted reserved words to double-quoted ones

    Args:
        sql: The SQL query string to process

    Returns:
        The SQL with reserved words properly quoted
    """
    try:
        # Parse the SQL
        parsed = sqlparse.parse(sql)[0]

        # Convert the parsed SQL back to string, but process tokens
        result = []
        for token in parsed.flatten():
            if token.ttype is sqlparse.tokens.Literal.String.Single:
                # Remove quotes and check if it's a reserved word
                value = token.value.strip("'")
                if value.upper() in SNOWFLAKE_RESERVED_WORDS:
                    # Convert to double-quoted identifier
                    result.append(f'"{value}"')
                else:
                    result.append(token.value)
            else:
                result.append(token.value)

        return "".join(result)
    except Exception as e:
        logger.warning(f"Failed to parse SQL for reserved words: {e}")
        return sql


class QueryStatus(str, Enum):
    """Valid data lake query status values."""

    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.DATA_ANALYTICS_READ),
        "readOnlyHint": True,
    }
)
async def get_alert_event_stats(
    alert_ids: Annotated[
        List[str],
        Field(
            description="List of alert IDs to analyze",
            examples=[["alert-123", "alert-456", "alert-789"]],
        ),
    ],
    time_window: Annotated[
        int,
        Field(
            description="The time window in minutes to group distinct events by",
            ge=1,
            le=60,
            default=30,
        ),
    ] = 30,
    start_date: Annotated[
        str | None,
        Field(
            description="Optional start date in ISO-8601 format. Defaults to start of today UTC.",
            examples=["2024-03-20T00:00:00Z"],
        ),
    ] = None,
    end_date: Annotated[
        str | None,
        Field(
            description="Optional end date in ISO-8601 format. Defaults to end of today UTC.",
            examples=["2024-03-20T00:00:00Z"],
        ),
    ] = None,
) -> Dict[str, Any]:
    """Analyze patterns and relationships across multiple alerts by aggregating their event data into time-based groups.

    For each time window (configurable from 1-60 minutes), the tool collects unique entities (IPs, emails, usernames,
    trace IDs) and alert metadata (IDs, rules, severities) to help identify related activities.

    Results are ordered chronologically with the most recent first, helping analysts identify temporal patterns,
    common entities, and potential incident scope.

    Returns:
        Dict containing:
        - success: Boolean indicating if the query was successful
        - status: Status of the query (e.g., "succeeded", "failed", "cancelled")
        - message: Error message if unsuccessful
        - results: List of query result rows
        - column_info: Dict containing column names and types
        - stats: Dict containing stats about the query
        - has_next_page: Boolean indicating if there are more results available
        - next_cursor: Cursor for fetching the next page of results, or null if no more pages
    """
    if time_window not in [1, 5, 15, 30, 60]:
        raise ValueError("Time window must be 1, 5, 15, 30, or 60")

    # Get default date range if not provided
    if not start_date or not end_date:
        default_start, default_end = _get_today_date_range()
        start_date = start_date or default_start
        end_date = end_date or default_end

    # Convert alert IDs list to SQL array
    alert_ids_str = ", ".join(f"'{aid}'" for aid in alert_ids)

    # Use the date strings directly (already in GraphQL format)
    start_date_str = start_date
    end_date_str = end_date

    query = f"""
SELECT
    DATE_TRUNC('DAY', cs.p_event_time) AS event_day,
    DATE_TRUNC('MINUTE', DATEADD('MINUTE', {time_window} * FLOOR(EXTRACT(MINUTE FROM cs.p_event_time) / {time_window}), 
        DATE_TRUNC('HOUR', cs.p_event_time))) AS time_{time_window}_minute,
    cs.p_log_type,
    cs.p_any_ip_addresses AS source_ips,
    cs.p_any_emails AS emails,
    cs.p_any_usernames AS usernames,
    cs.p_any_trace_ids AS trace_ids,
    COUNT(DISTINCT cs.p_alert_id) AS alert_count,
    ARRAY_AGG(DISTINCT cs.p_alert_id) AS alert_ids,
    ARRAY_AGG(DISTINCT cs.p_rule_id) AS rule_ids,
    MIN(cs.p_event_time) AS first_event,
    MAX(cs.p_event_time) AS last_event,
    ARRAY_AGG(DISTINCT cs.p_alert_severity) AS severities
FROM
    panther_signals.public.correlation_signals cs
WHERE
    cs.p_alert_id IN ({alert_ids_str})
AND 
    cs.p_event_time BETWEEN '{start_date_str}' AND '{end_date_str}'
GROUP BY
    event_day,
    time_{time_window}_minute,
    cs.p_log_type,
    cs.p_any_ip_addresses,
    cs.p_any_emails,
    cs.p_any_usernames,
    cs.p_any_trace_ids
HAVING
    COUNT(DISTINCT cs.p_alert_id) > 0
ORDER BY
    event_day DESC,
    time_{time_window}_minute DESC,
    alert_count DESC
"""
    return await query_data_lake(query, "panther_signals.public", max_rows=100)


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.DATA_ANALYTICS_READ),
        "readOnlyHint": True,
    }
)
async def query_data_lake(
    sql: Annotated[
        str,
        Field(
            description="The SQL query to execute. Must include a p_event_time filter condition after WHERE or AND. The query must be compatible with Snowflake SQL."
        ),
    ],
    database_name: str = "panther_logs.public",
    timeout: Annotated[
        int,
        Field(
            description="Timeout in seconds before the SQL query is cancelled. If the query fails due to timeout, the caller should consider a longer timeout."
        ),
    ] = 30,
    max_rows: Annotated[
        int,
        Field(
            description="Maximum number of result rows to return (prevents context overflow)",
            ge=1,
            le=999,
        ),
    ] = 100,
    cursor: Annotated[
        str | None,
        Field(
            description="Optional pagination cursor from previous query to fetch next page of results",
        ),
    ] = None,
) -> Dict[str, Any]:
    """Query Panther's security data lake using SQL for log analysis and threat hunting.

    REQUIRED: Include time filter with p_event_time (required for performance and partitioning)

    Panther Time Filter Macros (Recommended - optimized for performance):
    - p_occurs_since(timeOffset [, tableAlias[, column]])
      Examples: p_occurs_since('1 d'), p_occurs_since('6 h'), p_occurs_since('2 weeks'), p_occurs_since(3600)
      Time formats: '30 s', '15 m', '6 h', '2 d', '1 w' OR '2 weeks', '1 day' OR numeric seconds

    - p_occurs_between(startTime, endTime [, tableAlias[, column]])
      Examples: p_occurs_between('2024-01-01', '2024-01-02'), p_occurs_between('2024-03-20T00:00:00Z', '2024-03-20T23:59:59Z')

    - p_occurs_around(timestamp, timeOffset [, tableAlias[, column]])
      Example: p_occurs_around('2024-01-15T10:30:00Z', '1 h')  # ±1 hour around timestamp

    - p_occurs_after(timestamp [, tableAlias[, column]])
    - p_occurs_before(timestamp [, tableAlias[, column]])

    Alternative (manual): WHERE p_event_time >= '2024-01-01' AND p_event_time < '2024-01-02'

    Best Practices:
    - Always use time filters (macros preferred over manual p_event_time conditions)
    - Start with summary queries, then drill down to specific timeframes
    - Use p_any_* fields for faster correlation (p_any_ip_addresses, p_any_usernames, p_any_emails)
    - Query specific fields instead of SELECT * for better performance

    Pagination:
    - First call: No cursor parameter - returns first page with max_rows results
    - Subsequent calls: Use next_cursor from previous response to get next page
    - Continue until has_next_page is False

    Common Examples:
    - Recent failed logins: "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_occurs_since('1 d') AND errorcode IS NOT NULL"
    - IP activity summary: "SELECT sourceippaddress, COUNT(*) FROM panther_logs.public.aws_cloudtrail WHERE p_occurs_since('6 h') GROUP BY sourceippaddress"
    - User correlation: "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_occurs_since('2 h') AND ARRAY_CONTAINS('user@domain.com'::VARIANT, p_any_emails)"
    - Nested field access: "SELECT p_enrichment:ipinfo_privacy:\"context.ip_address\" FROM table WHERE p_occurs_since('1 h')"

    Query Syntax (Snowflake SQL):
    - Access nested JSON: column:field.subfield
    - Quote special characters: column:"field name" or p_enrichment:"context.ip_address"
    - Array searches: ARRAY_CONTAINS('value'::VARIANT, array_column)

    Returns:
        Dict with query results:
        - results: List of matching rows (paginated based on cursor parameter)
        - results_truncated: True if results were truncated (only for non-paginated requests)
        - total_rows_available: Total rows found (for non-paginated requests)
        - has_next_page: True if more results are available
        - next_cursor: Cursor for next page (use in subsequent call)
        - column_info: Column names and data types
        - stats: Query performance metrics (execution time, bytes scanned)
        - success/status/message: Query execution status
    """
    logger.info("Executing data lake query")

    start_time = time.time()

    # Validate that the query includes a time filter (p_event_time or Panther macros)
    sql_lower = sql.lower().replace("\n", " ")
    has_p_event_time = re.search(
        r"\b(where|and)\s+.*?(?:[\w.]+\.)?p_event_time\s*(>=|<=|=|>|<|between)",
        sql_lower,
    )
    has_panther_macros = re.search(
        r"p_occurs_(since|between|around|after|before)\s*\(",
        sql_lower,
    )

    if (not (has_p_event_time or has_panther_macros)) and re.search(
        r"\Wpanther_(views|signals|rule_matches|rule_errors|monitor|logs|cloudsecurity)\.",
        sql_lower,
    ):
        error_msg = "Query must include a time filter: either `p_event_time` condition or Panther macro (p_occurs_since, p_occurs_between, etc.)"
        logger.error(error_msg)
        return {
            "success": False,
            "message": error_msg,
            "query_id": None,
        }

    try:
        # Process reserved words in the SQL
        processed_sql = wrap_reserved_words(sql)
        logger.debug(f"Original SQL: {sql}")
        logger.debug(f"Processed SQL: {processed_sql}")

        # Prepare input variables
        variables = {"input": {"sql": processed_sql, "databaseName": database_name}}

        logger.debug(f"Query variables: {variables}")

        # Execute the query asynchronously
        async with await _create_panther_client() as session:
            result = await session.execute(
                EXECUTE_DATA_LAKE_QUERY, variable_values=variables
            )

        # Get query ID from result
        query_id = result.get("executeDataLakeQuery", {}).get("id")

        if not query_id:
            raise ValueError("No query ID returned from execution")

        logger.info(f"Successfully executed query with ID: {query_id}")

        sleep_time = INITIAL_QUERY_SLEEP_SECONDS
        while True:
            await asyncio.sleep(sleep_time)

            result = await _get_data_lake_query_results(
                query_id=query_id, max_rows=max_rows, cursor=cursor
            )

            if result.get("status") == "running":
                if (time.time() - start_time) >= timeout:
                    await _cancel_data_lake_query(query_id=query_id)
                    return {
                        "success": False,
                        "status": "cancelled",
                        "message": "Query time exceeded timeout, and has been cancelled. A longer timout may be required. "
                        "Retrying may be faster due to caching, or you may need to reduce the duration of data being queried.",
                        "query_id": query_id,
                    }
            else:
                return result

            if sleep_time <= MAX_QUERY_SLEEP_SECONDS:
                sleep_time += 1
    except Exception as e:
        logger.error(f"Failed to execute data lake query: {str(e)}")
        # Try to get query_id if it was set before the error
        query_id = locals().get("query_id")
        return {
            "success": False,
            "message": f"Failed to execute data lake query: {str(e)}",
            "query_id": query_id,
        }


async def _get_data_lake_query_results(
    query_id: Annotated[
        str,
        Field(
            description="The ID of the query to get results for",
            examples=["01be5f14-0206-3c48-000d-9eff005dd176"],
        ),
    ],
    max_rows: int = 100,
    cursor: str | None = None,
) -> Dict[str, Any]:
    """Get the results of a previously executed data lake query.

    Returns:
        Dict containing:
        - success: Boolean indicating if the query was successful
        - status: Status of the query (e.g., "succeeded", "running", "failed", "cancelled")
        - message: Error message if unsuccessful
        - results: List of query result rows
        - column_info: Dict containing column names and types
        - stats: Dict containing stats about the query
        - has_next_page: Boolean indicating if there are more results available
        - next_cursor: Cursor for fetching the next page of results, or null if no more pages
    """
    logger.info(f"Fetching data lake queryresults for query ID: {query_id}")

    try:
        # Prepare input variables for pagination
        variables = {
            "id": query_id,
            "root": False,
            "resultsInput": {
                "pageSize": max_rows,
                "cursor": cursor,
            },
        }

        if cursor:
            logger.info(f"Using pagination cursor: {cursor}")

        logger.debug(f"Query variables: {variables}")

        # Execute the query asynchronously
        async with await _create_panther_client() as session:
            result = await session.execute(
                GET_DATA_LAKE_QUERY, variable_values=variables
            )

        # Get query data
        query_data = result.get("dataLakeQuery", {})

        if not query_data:
            logger.warning(f"No query found with ID: {query_id}")
            return {
                "success": False,
                "message": f"No query found with ID: {query_id}",
                "query_id": query_id,
            }

        # Get query status
        status = query_data.get("status")
        if status == "running":
            return {
                "success": True,
                "status": "running",
                "message": "Query is still running",
                "query_id": query_id,
            }
        elif status == "failed":
            return {
                "success": False,
                "status": "failed",
                "message": query_data.get("message", "Query failed"),
                "query_id": query_id,
            }
        elif status == "cancelled":
            return {
                "success": False,
                "status": "cancelled",
                "message": "Query was cancelled",
                "query_id": query_id,
            }

        # Get results data
        results = query_data.get("results", {})
        edges = results.get("edges", [])
        column_info = results.get("columnInfo", {})
        stats = results.get("stats", {})

        # Extract results from edges
        query_results = [edge["node"] for edge in edges]

        # Check pagination info
        page_info = results.get("pageInfo", {})
        has_next_page = page_info.get("hasNextPage", False)
        end_cursor = page_info.get("endCursor")

        # Track pagination state
        original_count = len(query_results)

        # For cursor-based requests, we don't truncate since GraphQL handles pagination
        was_truncated = False
        if cursor:
            logger.info(
                f"Retrieved page of {len(query_results)} results using cursor pagination"
            )
        else:
            # For initial requests without cursor, apply legacy truncation if needed
            was_truncated = original_count > max_rows
            if was_truncated:
                query_results = query_results[:max_rows]
                logger.info(
                    f"Query results truncated from {original_count} to {max_rows} rows for context window protection"
                )
            else:
                logger.info(
                    f"Retrieved {len(query_results)} results (no truncation needed)"
                )

        logger.info(
            f"Successfully retrieved {len(query_results)} results for query ID: {query_id}"
        )

        # Format the response
        return {
            "success": True,
            "status": status,
            "results": query_results,
            "results_truncated": was_truncated,
            "total_rows_available": original_count,
            "rows_returned": len(query_results),
            "column_info": {
                "order": column_info.get("order", []),
                "types": column_info.get("types", {}),
            },
            "stats": {
                "bytes_scanned": stats.get("bytesScanned", 0),
                "execution_time": stats.get("executionTime", 0),
                "row_count": stats.get("rowCount", 0),
            },
            "has_next_page": has_next_page,
            "next_cursor": end_cursor,
            "message": query_data.get("message", "Query executed successfully"),
            "query_id": query_id,
        }
    except Exception as e:
        logger.error(f"Failed to fetch data lake query results: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch data lake query results: {str(e)}",
            "query_id": query_id,
        }


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.DATA_ANALYTICS_READ),
        "readOnlyHint": True,
    }
)
async def list_databases() -> Dict[str, Any]:
    """List all available datalake databases in Panther.

    Returns:
        Dict containing:
        - success: Boolean indicating if the query was successful
        - databases: List of databases, each containing:
            - name: Database name
            - description: Database description
        - message: Error message if unsuccessful
    """

    logger.info("Fetching datalake databases")

    try:
        # Execute the query asynchronously
        async with await _create_panther_client() as session:
            result = await session.execute(LIST_DATABASES_QUERY)

        # Get query data
        databases = result.get("dataLakeDatabases", [])

        if not databases:
            logger.warning("No databases found")
            return {"success": False, "message": "No databases found"}

        logger.info(f"Successfully retrieved {len(databases)} results")

        # Format the response
        return {
            "success": True,
            "status": "succeeded",
            "databases": databases,
            "stats": {
                "database_count": len(databases),
            },
        }
    except Exception as e:
        logger.error(f"Failed to fetch database results: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch database results: {str(e)}",
        }


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.DATA_ANALYTICS_READ),
        "readOnlyHint": True,
    }
)
async def list_database_tables(
    database: Annotated[
        str,
        Field(
            description="The name of the database to list tables for",
            examples=["panther_logs.public"],
        ),
    ],
) -> Dict[str, Any]:
    """List all available tables in a Panther Database.

    Required: Only use valid database names obtained from list_databases

    Returns:
        Dict containing:
        - success: Boolean indicating if the query was successful
        - tables: List of tables, each containing:
            - name: Table name
            - description: Table description
            - log_type: Log type
            - database: Database name
        - message: Error message if unsuccessful
    """
    logger.info("Fetching available tables")

    all_tables = []
    page_size = 100

    try:
        logger.info(f"Fetching tables for database: {database}")
        cursor = None

        while True:
            # Prepare input variables
            variables = {
                "databaseName": database,
                "pageSize": page_size,
                "cursor": cursor,
            }

            logger.debug(f"Query variables: {variables}")

            # Execute the query asynchronously
            async with await _create_panther_client() as session:
                result = await session.execute(
                    LIST_TABLES_QUERY, variable_values=variables
                )

            # Get query data
            result = result.get("dataLakeDatabaseTables", {})
            for table in result.get("edges", []):
                all_tables.append(table["node"])

            # Check if there are more pages
            page_info = result["pageInfo"]
            if not page_info["hasNextPage"]:
                break

            # Update cursor for next page
            cursor = page_info["endCursor"]

        # Format the response
        return {
            "success": True,
            "status": "succeeded",
            "tables": all_tables,
            "stats": {
                "table_count": len(all_tables),
            },
        }
    except Exception as e:
        logger.error(f"Failed to fetch tables: {str(e)}")
        return {"success": False, "message": f"Failed to fetch tables: {str(e)}"}


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.DATA_ANALYTICS_READ),
        "readOnlyHint": True,
    }
)
async def get_table_schema(
    database_name: Annotated[
        str,
        Field(
            description="The name of the database where the table is located",
            examples=["panther_logs.public"],
        ),
    ],
    table_name: Annotated[
        str,
        Field(
            description="The name of the table to get columns for",
            examples=["Panther.Audit"],
        ),
    ],
) -> Dict[str, Any]:
    """Get column details for a specific data lake table.

    IMPORTANT: This returns the table structure in Snowflake. For writing
    optimal queries, ALSO call get_panther_log_type_schema() to understand:
    - Nested object structures (only shown as 'object' type here)
    - Which fields map to p_any_* indicator columns
    - Array element structures

    Example workflow:
    1. get_panther_log_type_schema(["AWS.CloudTrail"]) - understand structure
    2. get_table_schema("panther_logs.public", "aws_cloudtrail") - get column names/types
    3. Write query using both: nested paths from log schema, column names from table schema

    Returns:
        Dict containing:
        - success: Boolean indicating if the query was successful
        - name: Table name
        - display_name: Table display name
        - description: Table description
        - log_type: Log type
        - columns: List of columns, each containing:
            - name: Column name
            - type: Column data type
            - description: Column description
        - message: Error message if unsuccessful
    """
    table_full_path = f"{database_name}.{table_name}"
    logger.info(f"Fetching column information for table: {table_full_path}")

    try:
        # Prepare input variables
        variables = {"databaseName": database_name, "tableName": table_name}

        logger.debug(f"Query variables: {variables}")

        # Execute the query asynchronously
        async with await _create_panther_client() as session:
            result = await session.execute(
                GET_COLUMNS_FOR_TABLE_QUERY, variable_values=variables
            )

        # Get query data
        query_data = result.get("dataLakeDatabaseTable", {})
        columns = query_data.get("columns", [])

        if not columns:
            logger.warning(f"No columns found for table: {table_full_path}")
            return {
                "success": False,
                "message": f"No columns found for table: {table_full_path}",
            }

        logger.info(f"Successfully retrieved {len(columns)} columns")

        # Format the response
        return {
            "success": True,
            "status": "succeeded",
            **query_data,
            "stats": {
                "table_count": len(columns),
            },
        }
    except Exception as e:
        logger.error(f"Failed to get columns for table: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to get columns for table: {str(e)}",
        }


async def _cancel_data_lake_query(
    query_id: Annotated[
        str,
        Field(description="The ID of the query to cancel"),
    ],
) -> Dict[str, Any]:
    """Cancel a running data lake query to free up resources and prevent system overload.

    This tool is critical for managing data lake performance and preventing resource exhaustion.
    Use it to cancel long-running queries that are consuming excessive resources or are no longer needed.

    IMPORTANT: Only running queries can be cancelled. Completed, failed, or already cancelled queries
    cannot be cancelled again.

    Common use cases:
    - Cancel runaway queries consuming too many resources
    - Stop queries that are taking longer than expected
    - Clean up queries that are no longer needed
    - Prevent system overload during peak usage

    Best practices:
    1. First use list_data_lake_queries(status=['running']) to find running queries
    2. Review the SQL and timing information before cancelling
    3. Cancel queries from oldest to newest if multiple queries need cancellation
    4. Monitor system load after cancellation to ensure improvement

    Returns:
        Dict containing:
        - success: Boolean indicating if the cancellation was successful
        - query_id: ID of the cancelled query
        - message: Success/error message
    """
    logger.info(f"Cancelling data lake query: {query_id}")

    try:
        client = await _create_panther_client()

        variables = {"input": {"id": query_id}}

        # Execute the cancellation
        async with client as session:
            result = await session.execute(
                CANCEL_DATA_LAKE_QUERY, variable_values=variables
            )

        # Parse results
        cancellation_data = result.get("cancelDataLakeQuery", {})
        cancelled_id = cancellation_data.get("id")

        if not cancelled_id:
            raise ValueError("No query ID returned from cancellation")

        logger.info(f"Successfully cancelled data lake query: {cancelled_id}")

        return {
            "success": True,
            "query_id": cancelled_id,
            "message": f"Successfully cancelled query {cancelled_id}",
        }

    except Exception as e:
        logger.error(f"Failed to cancel data lake query: {str(e)}")

        # Provide helpful error messages for common issues
        error_message = str(e)
        if "not found" in error_message.lower():
            error_message = f"Query {query_id} not found. It may have already completed or been cancelled."
        elif "cannot be cancelled" in error_message.lower():
            error_message = f"Query {query_id} cannot be cancelled. Only running queries can be cancelled."
        elif "permission" in error_message.lower():
            error_message = f"Permission denied. You may not have permission to cancel query {query_id}."
        else:
            error_message = f"Failed to cancel query {query_id}: {error_message}"

        return {
            "success": False,
            "message": error_message,
        }
