"""
Tools for interacting with Panther's data lake.
"""

import logging
from typing import Any, Dict

from ..client import _create_panther_client
from ..queries import (
    ALL_DATABASE_ENTITIES_QUERY,
    EXECUTE_DATA_LAKE_QUERY,
    GET_DATA_LAKE_QUERY,
)
from .registry import mcp_tool

logger = logging.getLogger("mcp-panther")


@mcp_tool
async def execute_data_lake_query(
    sql: str, database_name: str = "panther_logs.public"
) -> Dict[str, Any]:
    """Execute a Snowflake SQL query against Panther's data lake. RECOMMENDED: First query the information_schema.columns table for the PUBLIC table schema and the p_log_type to get the correct column names and types to query.

    Args:
        sql: The Snowflake SQL query to execute (tables are named after p_log_type)
        database_name: Optional database name to execute against ("panther_logs.public": all logs, "panther_rule_matches.public": rule matches)
    """
    logger.info("Executing data lake query")

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
async def get_data_lake_dbs_tables_columns(
    database: str = None, table: str = None
) -> Dict[str, Any]:
    """List all available databases, tables, and columns for querying Panther's data lake. Check this BEFORE running a data lake query.

    Args:
        database: Optional database name to filter results. Available databases:
            - panther_logs.public: Contains all log data
            - panther_cloudsecurity.public: Contains cloud security scanning data
            - panther_rule_errors.public: Contains rule execution errors
        table: Optional table name to filter results (e.g. "compliance_history")

    Returns:
        Dict containing:
        - success: Boolean indicating if the query was successful
        - databases: List of databases, each containing:
            - name: Database name
            - description: Database description
            - tables: List of tables, each containing:
                - name: Table name
                - description: Table description
                - columns: List of columns, each containing:
                    - name: Column name
                    - description: Column description
                    - type: Column data type
        - message: Error message if unsuccessful
    """
    logger.info("Fetching available databases, tables, and columns")

    try:
        client = await _create_panther_client()

        # Execute the query asynchronously
        async with client as session:
            result = await session.execute(ALL_DATABASE_ENTITIES_QUERY)

        # Get databases data
        databases = result.get("dataLakeDatabases", [])

        # Log unique database names
        unique_dbs = sorted({db["name"] for db in databases})
        logger.info(f"Available databases from API: {', '.join(unique_dbs)}")

        # Filter by database if specified
        if database:
            databases = [
                db for db in databases if db["name"].lower() == database.lower()
            ]
            if not databases:
                return {"success": False, "message": f"Database '{database}' not found"}

        # Filter by table if specified
        if table:
            for db in databases:
                db["tables"] = [
                    t for t in db["tables"] if t["name"].lower() == table.lower()
                ]
            # Only keep databases that have matching tables
            databases = [db for db in databases if db["tables"]]
            if not databases:
                return {
                    "success": False,
                    "message": f"Table '{table}' not found in any database",
                }

        logger.info(f"Successfully retrieved {len(databases)} databases")
        if database:
            logger.info(f"Filtered to database: {database}")
        if table:
            logger.info(f"Filtered to table: {table}")

        # Format the response
        return {
            "success": True,
            "databases": databases,
        }

    except Exception as e:
        logger.error(f"Failed to fetch data lake entities: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch data lake entities: {str(e)}",
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
