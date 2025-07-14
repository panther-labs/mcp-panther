"""
Tools for interacting with Panther's data lake.
"""

import logging
import re
from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Dict, List

import anyascii
from pydantic import Field

from ..client import _create_panther_client, get_today_date_range, graphql_date_format
from ..permissions import Permission, all_perms
from ..queries import (
    CANCEL_DATA_LAKE_QUERY,
    EXECUTE_DATA_LAKE_QUERY,
    GET_COLUMNS_FOR_TABLE_QUERY,
    GET_DATA_LAKE_QUERY,
    LIST_DATA_LAKE_QUERIES,
    LIST_DATABASES_QUERY,
    LIST_TABLES_QUERY,
)
from .registry import mcp_tool

logger = logging.getLogger("mcp-panther")


# Snowflake reserved words that can be quoted when used as column names
# Based on official Snowflake documentation

# Reserved by ANSI - can be quoted when used as column names
ANSI_RESERVED_WORDS = {
    "ALL", "ALTER", "AND", "ANY", "AS", "BETWEEN", "BY", "CHECK", "COLUMN", "CONNECT",
    "CREATE", "CURRENT", "DELETE", "DISTINCT", "DROP", "ELSE", "EXISTS", "FOR", "FROM",
    "GRANT", "GROUP", "HAVING", "IN", "INSERT", "INTERSECT", "INTO", "IS", "LIKE",
    "NOT", "NULL", "OF", "ON", "OR", "ORDER", "REVOKE", "ROW", "ROWS", "SAMPLE",
    "SELECT", "SET", "START", "TABLE", "TABLESAMPLE", "THEN", "TO", "TRIGGER",
    "UNION", "UNIQUE", "UPDATE", "VALUES", "WHENEVER", "WHERE", "WINDOW", "WITH",
}

# Reserved by Snowflake (non-ANSI) - can be quoted when used as column names
SNOWFLAKE_RESERVED_WORDS = {
    "ILIKE", "INCREMENT", "MINUS", "QUALIFY", "REGEXP", "RLIKE", "SOME",
}

# Additional words that cause issues in SELECT statements and can be quoted
ADDITIONAL_PROBLEMATIC_WORDS = {
    "ACCOUNT", "CONNECTION", "DATABASE", "GSCLUSTER", "ISSUE", "ORGANIZATION", "SCHEMA", "VIEW",
}

# Cannot be used as column reference in scalar expressions - should error
SCALAR_EXPRESSION_FORBIDDEN = {"CASE", "CAST", "FALSE", "TRUE", "TRY_CAST", "WHEN"}

# Cannot be used as column name (reserved by ANSI) - should error as column name
COLUMN_NAME_FORBIDDEN = {"CURRENT_USER", "LOCALTIME", "LOCALTIMESTAMP"}

# All quotable reserved words for Snowflake
QUOTABLE_RESERVED_WORDS = (
    ANSI_RESERVED_WORDS | SNOWFLAKE_RESERVED_WORDS | ADDITIONAL_PROBLEMATIC_WORDS
)


def _validate_and_wrap_reserved_words(sql: str) -> tuple[str, str | None]:
    """
    Validate and wrap reserved words according to Snowflake constraints.

    This implementation:
    - Wraps ANSI/Snowflake reserved words with double quotes when used as column names
    - Handles reserved words inside function calls (e.g., COUNT(DISTINCT account))
    - Returns errors for forbidden words in specific contexts
    - Provides lists of related reserved words in error messages

    Args:
        sql: The SQL query string to process

    Returns:
        Tuple of (processed_sql, error_message). If error_message is not None,
        the query contains forbidden usage and should be rejected.
    """
    # 1. Check for forbidden scalar expression words (but not function calls or SQL keywords)
    for forbidden_word in SCALAR_EXPRESSION_FORBIDDEN:
        # More precise check: exclude valid SQL contexts like CASE WHEN expressions
        if forbidden_word in ["CASE", "WHEN"]:
            # Skip CASE and WHEN when they're part of valid CASE expressions
            pattern = (
                r"\bSELECT\b[^;]*\b"
                + re.escape(forbidden_word)
                + r"\b(?!\s*\()(?![^,]*\b(?:WHEN|THEN|ELSE|END)\b)"
            )
        else:
            pattern = r"\bSELECT\b[^;]*\b" + re.escape(forbidden_word) + r"\b(?!\s*\()"

        if re.search(pattern, sql, re.IGNORECASE):
            forbidden_list = ", ".join(sorted(SCALAR_EXPRESSION_FORBIDDEN))
            return (
                sql,
                f"Query contains forbidden keyword usage: '{forbidden_word}' cannot be used as column reference in scalar expressions. "
                f"Forbidden scalar expression words: {forbidden_list}",
            )

    # 2. Check for forbidden column names (but not function calls)
    for forbidden_word in COLUMN_NAME_FORBIDDEN:
        # Simple check: if forbidden word appears after SELECT (as column), but not as function call
        pattern = r"\bSELECT\b[^;]*\b" + re.escape(forbidden_word) + r"\b(?!\s*\()"
        if re.search(pattern, sql, re.IGNORECASE):
            forbidden_list = ", ".join(sorted(COLUMN_NAME_FORBIDDEN))
            return (
                sql,
                f"Query contains forbidden keyword usage: '{forbidden_word}' cannot be used as column name (reserved by ANSI). "
                f"Forbidden column names: {forbidden_list}",
            )

    # 3. Quote reserved words in specific column contexts (including inside functions)
    # Only quote words that are actually problematic as column references
    column_context_words = QUOTABLE_RESERVED_WORDS - {
        # Exclude common SQL keywords that shouldn't be quoted when used as keywords
        "ALL", "AND", "AS", "BY", "DISTINCT", "ELSE", "EXISTS", "FOR", "FROM",
        "GROUP", "HAVING", "IN", "IS", "LIKE", "NOT", "NULL", "OF", "ON", "OR",
        "ORDER", "SELECT", "SET", "THEN", "TO", "UNION", "UPDATE", "WHERE", "WITH",
    }

    def quote_reserved_word_match(match):
        word = match.group(0)
        return f'"{word}"'

    # Build pattern for words that should be quoted in column contexts
    column_words = "|".join(re.escape(word) for word in column_context_words)

    # Pattern to match reserved words that should be quoted
    # (?<!["'`])       - Not preceded by quote
    # \b({words})\b    - Word boundary with reserved words
    # (?!\s*\()        - Not followed by opening parenthesis (function calls)
    reserved_word_pattern = rf"(?<![\"'`])\b({column_words})\b(?!\s*\()"

    # Apply the pattern only to the SELECT clause
    def process_select_clause(match):
        select_keyword = match.group(1)  # "SELECT"
        select_content = match.group(2)  # Everything after SELECT until FROM

        # Quote reserved words in the SELECT content
        processed_content = re.sub(
            reserved_word_pattern,
            quote_reserved_word_match,
            select_content,
            flags=re.IGNORECASE,
        )

        return select_keyword + processed_content

    # Pattern to match SELECT clause until FROM (including multiline)
    select_clause_pattern = r"\b(SELECT\s+)((?:[^;](?!FROM\s))*?)(?=\s+FROM\s)"
    modified_sql = re.sub(
        select_clause_pattern,
        process_select_clause,
        sql,
        flags=re.IGNORECASE | re.DOTALL,
    )

    return modified_sql, None


class QueryStatus(str, Enum):
    """Valid data lake query status values."""

    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.DATA_ANALYTICS_READ),
    }
)
async def summarize_alert_events(
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
        datetime | None,
        Field(
            description="The start date of the analysis period. Defaults to start of today UTC."
        ),
    ] = None,
    end_date: Annotated[
        datetime | None,
        Field(
            description="The end date of the analysis period. Defaults to end of today UTC."
        ),
    ] = None,
) -> Dict[str, Any]:
    """Analyze patterns and relationships across multiple alerts by aggregating their event data into time-based groups. For each time window (configurable from 1-60 minutes), the tool collects unique entities (IPs, emails, usernames, trace IDs) and alert metadata (IDs, rules, severities) to help identify related activities. Results are ordered chronologically with the most recent first, helping analysts identify temporal patterns, common entities, and potential incident scope.

    Returns a dictionary containing query execution details and a query_id for retrieving results.
    """
    if time_window not in [1, 5, 15, 30, 60]:
        raise ValueError("Time window must be 1, 5, 15, 30, or 60")

    # Get default date range if not provided
    if start_date is None or end_date is None:
        default_start, default_end = get_today_date_range()
        start_date = start_date or default_start
        end_date = end_date or default_end

    # Convert alert IDs list to SQL array
    alert_ids_str = ", ".join(f"'{aid}'" for aid in alert_ids)

    # Convert datetime objects to GraphQL format for SQL query
    start_date_str = graphql_date_format(start_date)
    end_date_str = graphql_date_format(end_date)

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
LIMIT 1000
"""
    return await execute_data_lake_query(query, "panther_signals.public")


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.DATA_ANALYTICS_READ),
    }
)
async def execute_data_lake_query(
    sql: Annotated[
        str,
        Field(
            description="The SQL query to execute. Must include a p_event_time filter condition after WHERE or AND. The query must be compatible with Snowflake SQL."
        ),
    ],
    database_name: str = "panther_logs.public",
) -> Dict[str, Any]:
    """Execute custom SQL queries against Panther's data lake for advanced data analysis and aggregation. This tool requires a p_event_time filter condition and should only be called five times per user request. For simple log sampling, use get_sample_log_events instead. The query must follow Snowflake SQL syntax (e.g., use field:nested_field instead of field.nested_field).

    WORKFLOW:
    1. First call get_table_schema to understand the schema
    2. Then execute_data_lake_query with your SQL
    3. Finally call get_data_lake_query_results with the returned query_id

    RESERVED WORDS HANDLING:
    - Snowflake reserved words are automatically quoted when used as column names
    - ANSI reserved words like 'column', 'order', 'table' are automatically handled
    - Functions like CURRENT_TIMESTAMP() are left unchanged
    - Forbidden words like 'false', 'true' return validation errors

    Returns a dictionary with query execution status and a query_id for retrieving results.
    """
    logger.info("Executing data lake query")

    # Validate and wrap reserved words according to Snowflake constraints
    sql, validation_error = _validate_and_wrap_reserved_words(sql)
    if validation_error:
        logger.error(validation_error)
        return {
            "success": False,
            "message": validation_error,
        }

    # Validate that the query includes a p_event_time filter after WHERE or AND
    sql_lower = sql.lower().replace("\n", " ")
    if not re.search(
        r"\b(where|and)\s+.*?(?:[\w.]+\.)?p_event_time\s*(>=|<=|=|>|<|between)",
        sql_lower,
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


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.DATA_ANALYTICS_READ),
    }
)
async def get_data_lake_query_results(
    query_id: Annotated[
        str,
        Field(
            description="The ID of the query to get results for",
            examples=["1234567890"],
        ),
    ],
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
        - end_cursor: Cursor for fetching the next page of results, or null if no more pages
    """
    logger.info(f"Fetching data lake queryresults for query ID: {query_id}")

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

        logger.info(
            f"Successfully retrieved {len(query_results)} results for query ID: {query_id}"
        )

        # Format the response
        return {
            "success": True,
            "status": status,
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
            "message": query_data.get("message", "Query executed successfully"),
        }
    except Exception as e:
        logger.error(f"Failed to fetch data lake query results: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch data lake query results: {str(e)}",
        }


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.DATA_ANALYTICS_READ),
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
    """Get column details for a specific datalake table.

    IMPORTANT: This returns the table structure in Snowflake/Redshift. For writing
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


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.DATA_ANALYTICS_READ),
        "readOnlyHint": True,
    }
)
async def get_sample_log_events(
    schema_name: Annotated[
        str,
        Field(
            description="The schema name to query for sample log events",
            examples=["Panther.Audit"],
        ),
    ],
) -> Dict[str, Any]:
    """Get a sample of 10 log events for a specific log type from the panther_logs.public database.

    This function is the RECOMMENDED tool for quickly exploring sample log data with minimal effort.

    This function constructs a SQL query to fetch recent sample events and executes it against
    the data lake. The query automatically filters events from the last 7 days to ensure quick results.

    NOTE: After calling this function, you MUST call get_data_lake_query_results with the returned
    query_id to retrieve the actual log events.

    Example usage:
        # Step 1: Get query_id for sample events
        result = get_sample_log_events(schema_name="Panther.Audit")

        # Step 2: Retrieve the actual results using the query_id
        events = get_data_lake_query_results(query_id=result["query_id"])

        # Step 3: Display results in a markdown table format

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

    logger.info(f"Fetching sample log events for schema: {schema_name}")

    database_name = "panther_logs.public"
    table_name = _normalize_name(schema_name)

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


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.DATA_ANALYTICS_READ),
        "readOnlyHint": True,
    }
)
async def list_data_lake_queries(
    cursor: str | None = None,
    page_size: Annotated[
        int,
        Field(
            description="The number of results that each page will contain. Defaults to 25 with a maximum value of 999.",
            ge=1,
            le=999,
        ),
    ] = 25,
    contains: Annotated[
        str | None,
        Field(description="Filter queries by their name and/or SQL statement"),
    ] = None,
    status: Annotated[
        list[QueryStatus] | None,
        Field(description="A list of query statuses to filter queries by"),
    ] = None,
    is_scheduled: Annotated[
        bool | None,
        Field(
            description="Only return queries that are either scheduled or not (i.e. issued by a user). Leave blank to return both."
        ),
    ] = None,
    started_at_after: Annotated[
        datetime | None,
        Field(description="Only return queries that started after this date"),
    ] = None,
    started_at_before: Annotated[
        datetime | None,
        Field(description="Only return queries that started before this date"),
    ] = None,
) -> Dict[str, Any]:
    """List previously executed data lake queries with comprehensive filtering options.

    This tool is essential for monitoring data lake query load and diagnosing performance issues.
    Use it to find long-running queries, check query history, or identify queries that need cancellation.

    Common use cases:
    - Find running queries: status=['running']
    - Monitor recent query activity: started_at_after='2024-01-01T00:00:00.000Z'
    - Search for specific queries: contains='SELECT * FROM alerts'
    - Check user vs scheduled queries: is_scheduled=false

    Returns:
        Dict containing:
        - success: Boolean indicating if the query was successful
        - queries: List of query objects with id, sql, status, timing info, and issuer details
        - page_info: Pagination information (hasNextPage, endCursor, etc.)
        - total_queries: Number of queries in current page
        - message: Error message if unsuccessful
    """
    logger.info("Listing data lake queries")

    try:
        client = await _create_panther_client()

        # Build input parameters
        input_params = {
            "pageSize": page_size,
        }

        if cursor:
            input_params["cursor"] = cursor
        if contains:
            input_params["contains"] = contains
        if status:
            input_params["status"] = [s.value for s in status]
        if is_scheduled is not None:
            input_params["isScheduled"] = is_scheduled
        if started_at_after:
            input_params["startedAtAfter"] = graphql_date_format(started_at_after)
        if started_at_before:
            input_params["startedAtBefore"] = graphql_date_format(started_at_before)

        variables = {"input": input_params} if input_params else None

        # Execute the query
        async with client as session:
            result = await session.execute(
                LIST_DATA_LAKE_QUERIES, variable_values=variables
            )

        # Parse results
        query_data = result.get("dataLakeQueries", {})
        edges = query_data.get("edges", [])
        page_info = query_data.get("pageInfo", {})

        # Extract queries from edges
        queries = []
        for edge in edges:
            node = edge["node"]
            # Format the issuer information
            issued_by = node.get("issuedBy")
            issuer_info = None
            if issued_by:
                if "email" in issued_by:  # User
                    issuer_info = {
                        "type": "user",
                        "id": issued_by.get("id"),
                        "email": issued_by.get("email"),
                        "name": f"{issued_by.get('givenName', '')} {issued_by.get('familyName', '')}".strip(),
                    }
                else:  # API Token
                    issuer_info = {
                        "type": "api_token",
                        "id": issued_by.get("id"),
                        "name": issued_by.get("name"),
                    }

            queries.append(
                {
                    "id": node.get("id"),
                    "sql": node.get("sql"),
                    "name": node.get("name"),
                    "status": node.get("status"),
                    "message": node.get("message"),
                    "started_at": node.get("startedAt"),
                    "completed_at": node.get("completedAt"),
                    "is_scheduled": node.get("isScheduled"),
                    "issued_by": issuer_info,
                }
            )

        logger.info(f"Successfully retrieved {len(queries)} data lake queries")

        return {
            "success": True,
            "queries": queries,
            "page_info": {
                "has_next_page": page_info.get("hasNextPage", False),
                "end_cursor": page_info.get("endCursor"),
                "has_previous_page": page_info.get("hasPreviousPage", False),
                "start_cursor": page_info.get("startCursor"),
            },
            "total_queries": len(queries),
        }

    except Exception as e:
        logger.error(f"Failed to list data lake queries: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to list data lake queries: {str(e)}",
        }


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.DATA_ANALYTICS_READ),
        "destructiveHint": True,
    }
)
async def cancel_data_lake_query(
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
