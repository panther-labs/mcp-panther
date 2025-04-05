"""
Tools for interacting with Panther's data lake.
"""

import logging
from typing import Dict, Any

from ..client import _create_panther_client
from ..queries import (
    EXECUTE_DATA_LAKE_QUERY,
    GET_DATA_LAKE_QUERY,
    ALL_DATABASE_ENTITIES_QUERY,
    LIST_SCHEMAS_QUERY,
    GET_SCHEMA_DETAILS_QUERY,
)
from .registry import mcp_tool

logger = logging.getLogger("mcp-panther")


@mcp_tool
async def execute_data_lake_query(
    sql: str, database_name: str = "panther_logs"
) -> Dict[str, Any]:
    """Execute a Snowflake SQL query against Panther's data lake. RECOMMENDED: First query the information_schema.columns table for the PUBLIC table schema and the p_log_type to get the correct column names and types to query.

    Args:
        sql: The Snowflake SQL query to execute (tables are named after p_log_type)
        database_name: Optional database name to execute against ("panther_logs.public": all logs, "panther_rule_matches.public": rule matches)
    """
    logger.info("Executing data lake query")

    try:
        client = _create_panther_client()

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
        client = _create_panther_client()

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
        client = _create_panther_client()

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
async def list_schemas(
    contains: str = None,
    is_archived: bool = None,
    is_in_use: bool = None,
    is_managed: bool = None,
) -> Dict[str, Any]:
    """List all available schemas (Log Types) in Panther. Schemas are transformation instructions that convert raw audit logs
    into structured data for the data lake and real-time Python rules.

    Note: Pagination is not currently supported - all schemas will be returned in the first page.

    Args:
        contains: Optional filter by name or schema field name
        is_archived: Optional filter by archive status
        is_in_use: Optional filter used/not used schemas
        is_managed: Optional filter by pack managed schemas

    Returns:
        Dict containing:
        - success: Boolean indicating if the query was successful
        - schemas: List of schemas, each containing:
            - name: Schema name (Log Type)
            - description: Schema description
            - revision: Schema revision number
            - isArchived: Whether the schema is archived
            - isManaged: Whether the schema is managed by a pack
            - referenceURL: Optional documentation URL
            - createdAt: Creation timestamp
            - updatedAt: Last update timestamp
        - message: Error message if unsuccessful
    """
    logger.info("Fetching available schemas")

    try:
        client = _create_panther_client()

        # Prepare input variables, only including non-None values
        input_vars = {}
        if contains is not None:
            input_vars["contains"] = contains
        if is_archived is not None:
            input_vars["isArchived"] = is_archived
        if is_in_use is not None:
            input_vars["isInUse"] = is_in_use
        if is_managed is not None:
            input_vars["isManaged"] = is_managed

        variables = {"input": input_vars}

        # Execute the query asynchronously
        async with client as session:
            result = await session.execute(
                LIST_SCHEMAS_QUERY, variable_values=variables
            )

        # Get schemas data and ensure we have the required structure
        schemas_data = result.get("schemas")
        if not schemas_data:
            return {"success": False, "message": "No schemas data returned from server"}

        edges = schemas_data.get("edges", [])

        schemas = [edge["node"] for edge in edges] if edges else []

        logger.info(f"Successfully retrieved {len(schemas)} schemas")

        # Format the response
        return {
            "success": True,
            "schemas": schemas,
        }

    except Exception as e:
        logger.error(f"Failed to fetch schemas: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch schemas: {str(e)}",
        }


@mcp_tool
async def get_schema_details(schema_names: list[str]) -> Dict[str, Any]:
    """Get detailed information for specific schemas, including their full specifications.
    Limited to 5 schemas at a time to prevent response size issues.

    Args:
        schema_names: List of schema names to get details for (max 5)

    Returns:
        Dict containing:
        - success: Boolean indicating if the query was successful
        - schemas: List of schemas, each containing:
            - name: Schema name (Log Type)
            - description: Schema description
            - spec: Schema specification in YAML/JSON format
            - version: Schema version number
            - revision: Schema revision number
            - isArchived: Whether the schema is archived
            - isManaged: Whether the schema is managed by a pack
            - isFieldDiscoveryEnabled: Whether automatic field discovery is enabled
            - referenceURL: Optional documentation URL
            - discoveredSpec: The schema discovered spec
            - createdAt: Creation timestamp
            - updatedAt: Last update timestamp
        - message: Error message if unsuccessful
    """
    if not schema_names:
        return {"success": False, "message": "No schema names provided"}

    if len(schema_names) > 5:
        return {
            "success": False,
            "message": "Maximum of 5 schema names allowed per request",
        }

    logger.info(f"Fetching detailed schema information for: {', '.join(schema_names)}")

    try:
        client = _create_panther_client()
        all_schemas = []

        # Query each schema individually to ensure we get exact matches
        for name in schema_names:
            variables = {"name": name}  # Pass single name as string

            async with client as session:
                result = await session.execute(
                    GET_SCHEMA_DETAILS_QUERY, variable_values=variables
                )

            schemas_data = result.get("schemas")
            if not schemas_data:
                logger.warning(f"No schema data found for {name}")
                continue

            edges = schemas_data.get("edges", [])
            # The query now returns exact matches, so we can use all results
            matching_schemas = [edge["node"] for edge in edges]

            if matching_schemas:
                all_schemas.extend(matching_schemas)
            else:
                logger.warning(f"No match found for schema {name}")

        if not all_schemas:
            return {"success": False, "message": "No matching schemas found"}

        logger.info(f"Successfully retrieved {len(all_schemas)} schemas")

        return {
            "success": True,
            "schemas": all_schemas,
        }

    except Exception as e:
        logger.error(f"Failed to fetch schema details: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch schema details: {str(e)}",
        }
