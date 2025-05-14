"""
Tools for interacting with Panther's data lake.
"""

import logging
import re
from typing import Any, Dict, Optional

import anyascii

from ..client import _create_panther_client
from ..queries import (
    EXECUTE_DATA_LAKE_QUERY,
    GET_COLUMNS_FOR_TABLE_QUERY,
    GET_DATA_LAKE_QUERY,
    LIST_DATABASES_QUERY,
    LIST_TABLES_FOR_DATABASE_QUERY,
    LIST_TABLES_QUERY,
)
from .registry import mcp_tool

logger = logging.getLogger("mcp-panther")


@mcp_tool
async def get_alert_event_summaries(alert_ids: list[str], time_window: int = 30):
    """Gather a summary of one or more alert's events. This is helpful for prioritizing and identifying relationships.

    This tool gathers stats on p_ fields from alerts that occurred within a shared time window.
    It takes a list of alert IDs and groups them by day, a time bucket, log type, source IPs, emails, usernames, and trace IDs to identify patterns of related activity.
    For each group, it counts alerts, collects alert IDs, rule IDs, timestamps, and severity levels, then sorts the results chronologically with the most recent events first.

    Args:
        alert_ids: List of alert IDs to analyze
        time_window: The time window in minutes to group distinct events by (must be 1, 5, 15, 30, or 60)

    Example:
        alert_ids = ["alert-123", "alert-456", "alert-789"]
    """
    if time_window not in [1, 5, 15, 30, 60]:
        raise ValueError("Time window must be 1, 5, 15, 30, or 60")

    # Convert alert IDs list to SQL array
    alert_ids_str = ", ".join(f"'{aid}'" for aid in alert_ids)

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
LIMIT 1000
"""
    return await execute_data_lake_query(query, "panther_signals.public")


@mcp_tool
async def execute_data_lake_query(
    sql: str, database_name: Optional[str] = "panther_logs.public"
) -> Dict[str, Any]:
    """Execute a performant Snowflake SQL query against Panther's data lake.

    IMPORTANT: This function is best for ADVANCED QUERIES with custom filtering, joins,
    or aggregations. For simple log sampling, use get_sample_log_events instead.

    REQUIREMENTS:
    1. USE THE get_table_columns TOOL FIRST to get the correct table schema.
    2. THE QUERY MUST INCLUDE A FILTER ON p_event_time WITH A MAX TIME DURATION OF 90 DAYS.
    3. Check the size of the table with get_bytes_processed_per_log_type_and_source. If the table is large, use smaller time windows and more specific filters.

    NOTE: After calling this function, you MUST call get_data_lake_query_results with the
    returned query_id to retrieve the actual query results.

    Example usage:
        # Step 1: Get table schema
        schema = get_table_columns(database_name="panther_logs.public", table_name="panther_audit")

        # Step 2: Execute query with required p_event_time filter
        result = execute_data_lake_query(
            sql="SELECT * FROM panther_logs.public.panther_audit WHERE p_event_time >= DATEADD(day, -30, CURRENT_TIMESTAMP()) LIMIT 10"
        )

        # Step 3: Retrieve the actual results using the query_id
        if result["success"]:
            query_results = get_data_lake_query_results(query_id=result["query_id"])

    Args:
        sql: The SQL query to execute (must include p_event_time filter)
        database_name: The database to query (default: "panther_logs.public")

    Returns:
        Dict containing:
        - success: Boolean indicating if the query was successful
        - query_id: ID of the executed query for retrieving results with get_data_lake_query_results
        - message: Error message if unsuccessful
    """

    logger.info("Executing data lake query")

    # Validate that the query includes a p_event_time filter after WHERE or AND
    sql_lower = sql.lower().replace("\n", " ")
    if not re.search(
        r"\b(where|and)\s+.*?p_event_time\s*(>=|<=|=|>|<|between)", sql_lower
    ):
        error_msg = (
            "Query must include p_event_time as a filter condition after WHERE or AND"
        )
        logger.error(error_msg)
        return {
            "success": False,
            "message": error_msg,
        }

    try:
        client = await _create_panther_client()

        # Prepare input variables
        variables = {"input": {"sql": sql, "databaseName": database_name}}

        logger.debug(f"Query variables: {variables}")

        # Execute the query asynchronously
        async with client as session:
            result = await session.execute(
                EXECUTE_DATA_LAKE_QUERY, variable_values=variables
            )

        # Get query ID from result
        query_id = result.get("executeDataLakeQuery", {}).get("id")

        if not query_id:
            raise ValueError("No query ID returned from execution")

        logger.info(f"Successfully executed query with ID: {query_id}")

        # Format the response
        return {"success": True, "query_id": query_id}
    except Exception as e:
        logger.error(f"Failed to execute data lake query: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to execute data lake query: {str(e)}",
        }


@mcp_tool
async def get_data_lake_query_results(query_id: str) -> Dict[str, Any]:
    """Get the results of a previously executed data lake query.

    Args:
        query_id: The ID of the query to get results for
    """
    logger.info(f"Fetching results for query ID: {query_id}")

    try:
        client = await _create_panther_client()

        # Prepare input variables
        variables = {"id": query_id, "root": False}

        logger.debug(f"Query variables: {variables}")

        # Execute the query asynchronously
        async with client as session:
            result = await session.execute(
                GET_DATA_LAKE_QUERY, variable_values=variables
            )

        # Get query data
        query_data = result.get("dataLakeQuery", {})

        if not query_data:
            logger.warning(f"No query found with ID: {query_id}")
            return {"success": False, "message": f"No query found with ID: {query_id}"}

        # Get query status
        status = query_data.get("status")
        if status == "running":
            return {
                "success": True,
                "status": "running",
                "message": "Query is still running",
            }
        elif status == "failed":
            return {
                "success": False,
                "status": "failed",
                "message": query_data.get("message", "Query failed"),
            }
        elif status == "cancelled":
            return {
                "success": False,
                "status": "cancelled",
                "message": "Query was cancelled",
            }

        # Get results data
        results = query_data.get("results", {})
        edges = results.get("edges", [])
        column_info = results.get("columnInfo", {})
        stats = results.get("stats", {})

        # Extract results from edges
        query_results = [edge["node"] for edge in edges]

        logger.info(f"Successfully retrieved {len(query_results)} results")

        # Format the response
        return {
            "success": True,
            "status": "succeeded",
            "results": query_results,
            "column_info": {
                "order": column_info.get("order", []),
                "types": column_info.get("types", {}),
            },
            "stats": {
                "bytes_scanned": stats.get("bytesScanned", 0),
                "execution_time": stats.get("executionTime", 0),
                "row_count": stats.get("rowCount", 0),
            },
            "has_next_page": results.get("pageInfo", {}).get("hasNextPage", False),
            "end_cursor": results.get("pageInfo", {}).get("endCursor"),
        }
    except Exception as e:
        logger.error(f"Failed to fetch query results: {str(e)}")
        return {"success": False, "message": f"Failed to fetch query results: {str(e)}"}


@mcp_tool
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
        client = await _create_panther_client()

        # Execute the query asynchronously
        async with client as session:
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


@mcp_tool
async def list_tables_for_database(database: str) -> Dict[str, Any]:
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
        client = await _create_panther_client()
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
            async with client as session:
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


@mcp_tool
async def get_tables_for_database(database_name: str) -> Dict[str, Any]:
    """Get all tables for a specific datalake database.

    Args:
        database_name: The name of the database to get tables for

    Returns:
        Dict containing:
        - success: Boolean indicating if the query was successful
        - tables: List of tables, each containing:
            - name: Table name
            - description: Table description
        - message: Error message if unsuccessful
    """
    logger.info(f"Fetching tables for database: {database_name}")

    try:
        client = await _create_panther_client()

        # Prepare input variables
        variables = {"name": database_name}

        logger.debug(f"Query variables: {variables}")

        # Execute the query asynchronously
        async with client as session:
            result = await session.execute(
                LIST_TABLES_FOR_DATABASE_QUERY, variable_values=variables
            )

        # Get query data
        query_data = result.get("dataLakeDatabase", {})
        tables = query_data.get("tables", [])

        if not tables:
            logger.warning(f"No tables found for database: {database_name}")
            return {
                "success": False,
                "message": f"No tables found for database: {database_name}",
            }

        logger.info(f"Successfully retrieved {len(tables)} tables")

        # Format the response
        return {
            "success": True,
            "status": "succeeded",
            "tables": tables,
            "stats": {
                "table_count": len(tables),
            },
        }
    except Exception as e:
        logger.error(f"Failed to get tables for database: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to get tables for database: {str(e)}",
        }


@mcp_tool
async def get_table_columns(database_name: str, table_name: str) -> Dict[str, Any]:
    """Get column details for a specific datalake table.

    Args:
        database_name: The name of the database where the table is located
        table_name: The name of the table to get columns for

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
        client = await _create_panther_client()

        # Prepare input variables
        variables = {"databaseName": database_name, "tableName": table_name}

        logger.debug(f"Query variables: {variables}")

        # Execute the query asynchronously
        async with client as session:
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


@mcp_tool
async def get_sample_log_events(log_type: str) -> Dict[str, Any]:
    """Get a sample of 10 log events for a specific log type from the panther_logs.public database.

    This function is the RECOMMENDED tool for quickly exploring sample log data with minimal effort.

    This function constructs a SQL query to fetch recent sample events and executes it against
    the data lake. The query automatically filters events from the last 7 days to ensure quick results.

    NOTE: After calling this function, you MUST call get_data_lake_query_results with the returned
    query_id to retrieve the actual log events.

    Example usage:
        # Step 1: Get query_id for sample events
        result = get_sample_log_events(log_type="Panther.Audit")

        # Step 2: Retrieve the actual results using the query_id
        if result["success"]:
            events = get_data_lake_query_results(query_id=result["query_id"])

            # Step 3: Display results in multiple formats for better analysis
            # Display as a formatted table for human readability
            display_table_format(events["results"])

            # Optionally provide JSON format for deeper inspection
            print(json.dumps(events["results"][0], indent=2))

    Args:
        log_type: The log type to query (this is also typically the table name)

    Returns:
        Dict containing:
        - success: Boolean indicating if the query was successful
        - query_id: ID of the executed query for retrieving results with get_data_lake_query_results
        - message: Error message if unsuccessful

    Post-processing:
        After retrieving results, it's recommended to:
        1. Display data in a table format (using artifacts for UI display)
        2. Provide sample JSON for a single record to show complete structure
        3. Highlight key fields and patterns across records
    """

    logger.info(f"Fetching sample log events for log type: {log_type}")

    database_name = "panther_logs.public"
    table_name = _normalize_name(log_type)

    try:
        sql = f"""
        SELECT *
        FROM {database_name}.{table_name}
        WHERE p_event_time >= DATEADD(day, -7, CURRENT_TIMESTAMP())
        ORDER BY p_event_time DESC
        LIMIT 10
        """

        result = await execute_data_lake_query(sql=sql, database_name=database_name)

        return result
    except Exception as e:
        logger.error(f"Failed to fetch sample log events: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch sample log events: {str(e)}",
        }


transliterate_chars = {
    "@": "at_sign",
    ",": "comma",
    "`": "backtick",
    "'": "apostrophe",
    "$": "dollar_sign",
    "*": "asterisk",
    "&": "ampersand",
    "!": "exclamation",
    "%": "percent",
    "+": "plus",
    "/": "slash",
    "\\": "backslash",
    "#": "hash",
    "~": "tilde",
    "=": "eq",
}

number_to_word = {
    "0": "zero",
    "1": "one",
    "2": "two",
    "3": "three",
    "4": "four",
    "5": "five",
    "6": "six",
    "7": "seven",
    "8": "eight",
    "9": "nine",
}


def _is_name_normalized(name):
    """Check if a table name is already normalized"""
    if not re.match(r"^[a-zA-Z_-][a-zA-Z0-9_-]*$", name):
        return False

    return True


def _normalize_name(name):
    """Normalize a table name"""
    if _is_name_normalized(name):
        return name

    result = []
    characters = list(name)
    last = len(characters) - 1

    for i, c in enumerate(characters):
        if "a" <= c <= "z" or "A" <= c <= "Z":
            # Allow uppercase and lowercase letters
            result.append(c)
        elif "0" <= c <= "9":
            if i == 0:
                # Convert numbers at the start of the string to words
                result.append(number_to_word[c])
                result.append("_")
            else:
                # Allow numbers beyond the first character
                result.append(c)
        elif c == "_" or c == "-":
            # Allow underscores and hyphens
            result.append(c)
        else:
            # Check if we have a specific transliteration for this character
            if c in transliterate_chars:
                if i > 0:
                    result.append("_")

                result.append(transliterate_chars[c])

                if i < last:
                    result.append("_")
                continue

            # Try to handle non-ASCII letters
            if ord(c) > 127:
                transliterated = anyascii.anyascii(c)
                if transliterated and transliterated != "'" and transliterated != " ":
                    result.append(transliterated)
                    continue

            # Fallback to underscore
            result.append("_")

    return "".join(result)
