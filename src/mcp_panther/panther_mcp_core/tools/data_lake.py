"""
Tools for interacting with Panther's data lake.
"""

import logging
from typing import Any, Dict, Optional

from ..client import _create_panther_client
from ..queries import (
    ALL_DATABASE_ENTITIES_QUERY,
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
async def execute_data_lake_query(
    sql: str, database_name: Optional[str] = "panther_logs.public"
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
async def list_tables() -> Dict[str, Any]:
    """List all available tables in Panther's data lake.

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

        # Execute the query asynchronously
        async with client as session:
            databases = await list_databases()

        for database in databases["databases"]:
            database_name = database["name"]
            logger.info(f"Fetching tables for database: {database_name}")

            cursor = None

            while True:
                # Prepare input variables
                variables = {
                    "databaseName": database_name,
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
                    table["node"]["database"] = database_name
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
