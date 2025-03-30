import logging
import os
import datetime
import sys
from typing import Dict, Any

from dotenv import load_dotenv
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from mcp.server.fastmcp import FastMCP
from mcp.server import stdio
from mcp.server.lowlevel.server import Server
import aiohttp

# Server name
MCP_SERVER_NAME = "mcp-panther"

# Configure logging with more detail
logging.basicConfig(
    level=logging.DEBUG,  # Change to DEBUG for more info
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,  # Ensure logs go to stderr
)
logger = logging.getLogger(MCP_SERVER_NAME)

# Load environment variables from .env file if it exists
load_dotenv()

# Server dependencies
deps = [
    "python-dotenv",
    "gql[aiohttp]",
    "aiohttp",
    "mcp[cli]",
]

# Create the MCP server
mcp = FastMCP(MCP_SERVER_NAME, dependencies=deps)

# GraphQL endpoint for Panther
PANTHER_GQL_API_URL = os.getenv(
    "PANTHER_GQL_API_URL", "https://api.runpanther.com/public/graphql"
)

# REST API endpoints for Panther
PANTHER_REST_API_URL = os.getenv("PANTHER_REST_API_URL", "https://api.runpanther.com")


# Get Panther API key from environment variable
def get_panther_api_key() -> str:
    api_key = os.getenv("PANTHER_API_KEY")
    if not api_key:
        raise ValueError("PANTHER_API_KEY environment variable is not set")
    return api_key


# GraphQL queries

GET_TODAYS_ALERTS_QUERY = gql("""
query FirstPageOfAllAlerts($input: AlertsInput!) {
    alerts(input: $input) {
        edges {
            node {
                id
                title
                severity
                status
                createdAt
                type
                description
                reference
                runbook
                firstEventOccurredAt
                lastReceivedEventAt
                origin {
                    ... on Detection {
                        id
                        name
                    }
                }
            }
        }
        pageInfo {
            hasNextPage
            endCursor
            hasPreviousPage
            startCursor
        }
    }
}
""")

GET_ALERT_BY_ID_QUERY = gql("""
query GetAlertById($id: ID!) {
    alert(id: $id) {
        id
        title
        severity
        status
        createdAt
        type
        description
        reference
        runbook
        firstEventOccurredAt
        lastReceivedEventAt
        updatedAt
        origin {
            ... on Detection {
                id
                name
            }
        }
    }
}
""")

GET_SOURCES_QUERY = gql("""
query Sources($input: SourcesInput) {
    sources(input: $input) {
        edges {
            node {
                integrationId
                integrationLabel
                integrationType
                isEditable
                isHealthy
                lastEventProcessedAtTime
                lastEventReceivedAtTime
                lastModified
                logTypes
                ... on S3LogIntegration {
                    awsAccountId
                    kmsKey
                    logProcessingRole
                    logStreamType
                    logStreamTypeOptions {
                        jsonArrayEnvelopeField
                    }
                    managedBucketNotifications
                    s3Bucket
                    s3Prefix
                    s3PrefixLogTypes {
                        prefix
                        logTypes
                        excludedPrefixes
                    }
                    stackName
                }
            }
        }
        pageInfo {
            hasNextPage
            hasPreviousPage
            startCursor
            endCursor
        }
    }
}
""")

EXECUTE_DATA_LAKE_QUERY = gql("""
mutation ExecuteDataLakeQuery($input: ExecuteDataLakeQueryInput!) {
    executeDataLakeQuery(input: $input) {
        id
    }
}
""")

GET_DATA_LAKE_QUERY = gql("""
query GetDataLakeQuery($id: ID!, $root: Boolean = false) {
    dataLakeQuery(id: $id, root: $root) {
        id
        status
        message
        sql
        startedAt
        completedAt
        results(input: { pageSize: 999 }) {
            edges {
                node
            }
            pageInfo {
                hasNextPage
                endCursor
            }
            columnInfo {
                order
                types
            }
            stats {
                bytesScanned
                executionTime
                rowCount
            }
        }
    }
}
""")


def _get_today_date_range() -> tuple:
    """Get date range for the last 24 hours (UTC)"""
    # Get current UTC time and shift back by one day since we're already in tomorrow
    now = datetime.datetime.now(datetime.timezone.utc)
    now = now - datetime.timedelta(days=1)

    # Get start of today (midnight UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Get end of today (midnight UTC of next day)
    today_end = today_start + datetime.timedelta(days=1)

    # Format for GraphQL query (ISO 8601 with milliseconds and Z suffix)
    start_date = today_start.isoformat(timespec="milliseconds").replace("+00:00", "Z")
    end_date = today_end.isoformat(timespec="milliseconds").replace("+00:00", "Z")

    logger.debug(f"Calculated date range - Start: {start_date}, End: {end_date}")
    return start_date, end_date


def _create_panther_client() -> Client:
    """Create a Panther GraphQL client with proper configuration"""
    transport = AIOHTTPTransport(
        url=PANTHER_GQL_API_URL,
        headers={"X-API-Key": get_panther_api_key()},
        ssl=True,  # Enable SSL verification
    )
    return Client(transport=transport, fetch_schema_from_transport=True)


@mcp.tool()
async def list_alerts(
    start_date: str = None,
    end_date: str = None,
    severities: list[str] = None,
    statuses: list[str] = None,
    cursor: str = None,
) -> Dict[str, Any]:
    """List alerts from Panther for a specified date range or the last 24 hours by default

    Args:
        start_date: Optional start date in ISO 8601 format (e.g. "2024-03-20T00:00:00Z")
        end_date: Optional end date in ISO 8601 format (e.g. "2024-03-21T00:00:00Z")
        severities: Optional list of severities to filter by (e.g. ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"])
        statuses: Optional list of statuses to filter by (e.g. ["OPEN", "TRIAGED", "RESOLVED", "CLOSED"])
        cursor: Optional cursor for pagination from a previous query
    """
    logger.info("Fetching alerts from Panther")

    try:
        client = _create_panther_client()

        # If no dates provided and no cursor, get the last 24 hours
        if not start_date and not end_date and not cursor:
            start_date, end_date = _get_today_date_range()
            logger.info(
                f"No date range provided, using last 24 hours: {start_date} to {end_date}"
            )
        elif not cursor:
            logger.info(f"Using provided date range: {start_date} to {end_date}")

        # Prepare input variables
        variables = {
            "input": {
                "pageSize": 25,  # Default page size
                "sortBy": "createdAt",  # Sort by creation date
                "sortDir": "descending",  # Most recent first
            }
        }

        # Add date filters if provided and no cursor
        if not cursor:
            if start_date:
                variables["input"]["createdAtAfter"] = start_date
            if end_date:
                variables["input"]["createdAtBefore"] = end_date

        # Add cursor if provided
        if cursor:
            variables["input"]["cursor"] = cursor
            logger.info(f"Using cursor for pagination: {cursor}")

        # Add severity filters if provided
        if severities:
            variables["input"]["severities"] = severities
            logger.info(f"Filtering by severities: {severities}")

        # Add status filters if provided
        if statuses:
            variables["input"]["statuses"] = statuses
            logger.info(f"Filtering by statuses: {statuses}")

        logger.debug(f"Query variables: {variables}")

        # Execute the query asynchronously
        async with client as session:
            result = await session.execute(
                GET_TODAYS_ALERTS_QUERY, variable_values=variables
            )

        # Log the raw result for debugging
        logger.debug(f"Raw query result: {result}")

        # Process results
        alerts_data = result.get("alerts", {})
        alert_edges = alerts_data.get("edges", [])
        page_info = alerts_data.get("pageInfo", {})

        # Extract alerts from edges
        alerts = [edge["node"] for edge in alert_edges]

        logger.info(f"Successfully retrieved {len(alerts)} alerts")

        # Format the response
        return {
            "success": True,
            "alerts": alerts,
            "total_alerts": len(alerts),
            "has_next_page": page_info.get("hasNextPage", False),
            "has_previous_page": page_info.get("hasPreviousPage", False),
            "end_cursor": page_info.get("endCursor"),
            "start_cursor": page_info.get("startCursor"),
        }
    except Exception as e:
        logger.error(f"Failed to fetch alerts: {str(e)}")
        return {"success": False, "message": f"Failed to fetch alerts: {str(e)}"}


@mcp.tool()
async def get_alert_by_id(alert_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific Panther alert by ID"""
    logger.info(f"Fetching alert details for ID: {alert_id}")
    try:
        client = _create_panther_client()

        # Prepare input variables
        variables = {"id": alert_id}

        # Execute the query asynchronously
        async with client as session:
            result = await session.execute(
                GET_ALERT_BY_ID_QUERY, variable_values=variables
            )

        # Get alert data
        alert_data = result.get("alert", {})

        if not alert_data:
            logger.warning(f"No alert found with ID: {alert_id}")
            return {"success": False, "message": f"No alert found with ID: {alert_id}"}

        logger.info(f"Successfully retrieved alert details for ID: {alert_id}")

        # Format the response
        return {"success": True, "alert": alert_data}
    except Exception as e:
        logger.error(f"Failed to fetch alert details: {str(e)}")
        return {"success": False, "message": f"Failed to fetch alert details: {str(e)}"}


@mcp.tool()
async def list_sources(
    cursor: str = None,
    log_types: list[str] = None,
    is_healthy: bool = None,
    integration_type: str = None,
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
        client = _create_panther_client()

        # Prepare input variables
        variables = {"input": {}}

        # Add cursor if provided
        if cursor:
            variables["input"]["cursor"] = cursor
            logger.info(f"Using cursor for pagination: {cursor}")

        # Add log types filter if provided
        if log_types:
            variables["input"]["logTypes"] = log_types
            logger.info(f"Filtering by log types: {log_types}")

        # Add health status filter if provided
        if is_healthy is not None:
            variables["input"]["isHealthy"] = is_healthy
            logger.info(f"Filtering by health status: {is_healthy}")

        # Add integration type filter if provided
        if integration_type:
            variables["input"]["integrationType"] = integration_type
            logger.info(f"Filtering by integration type: {integration_type}")

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


@mcp.tool()
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


@mcp.tool()
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


@mcp.prompt()
def triage_alert(alert_id: str) -> str:
    return f"""You are an expert cyber security analyst. Follow these steps to triage a Panther alert:
    1. Get the alert details for alert ID {alert_id}
    2. Query the data lake to read all associated events (database: panther_rule_matches.public, table: log type from the alert)
    3. Determine alert judgment based on common attacker patterns and techniques (benign, false positive, true positive, or a custom judgment).
    """


@mcp.prompt()
def prioritize_alerts() -> str:
    return """You are an expert cyber security analyst. Your goal is to prioritize alerts based on severity, impact, and other relevant criteria to decide which alerts to investigate first. Use the following steps to prioritize alerts:
    1. List all alerts in the last 24 hours and logically group them by user, host, or other similar criteria. Alerts can be related even if they have different titles or log types (for example, if a user logs into Okta and then AWS).
    2. Triage each group of alerts to understand what happened and what the impact was. Query the data lake to read all associated events (database: panther_rule_matches.public, table: log type from the alert) and use the results to understand the impact.
    3. Create next steps for each group of alerts to investigate and resolve.
    """


@mcp.tool()
async def list_rules(cursor: str = None, limit: int = 100) -> Dict[str, Any]:
    """List all rules from Panther with optional pagination

    Args:
        cursor: Optional cursor for pagination from a previous query
        limit: Optional maximum number of results to return (default: 100)
    """
    logger.info("Fetching rules from Panther")

    try:
        # Prepare headers
        headers = {
            "X-API-Key": get_panther_api_key(),
            "Content-Type": "application/json",
        }

        # Prepare query parameters
        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
            logger.info(f"Using cursor for pagination: {cursor}")

        # Make the request
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{PANTHER_REST_API_URL}/rules", headers=headers, params=params
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Failed to fetch rules: {error_text}")

                result = await response.json()

        # Extract rules and pagination info
        rules = result.get("results", [])
        next_cursor = result.get("next")

        logger.info(f"Successfully retrieved {len(rules)} rules")

        # Format the response
        return {
            "success": True,
            "rules": rules,
            "total_rules": len(rules),
            "has_next_page": bool(next_cursor),
            "next_cursor": next_cursor,
        }
    except Exception as e:
        logger.error(f"Failed to fetch rules: {str(e)}")
        return {"success": False, "message": f"Failed to fetch rules: {str(e)}"}


@mcp.tool()
async def get_rule_by_id(rule_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific Panther rule by ID

    Args:
        rule_id: The ID of the rule to fetch
    """
    logger.info(f"Fetching rule details for ID: {rule_id}")

    try:
        # Prepare headers
        headers = {
            "X-API-Key": get_panther_api_key(),
            "Content-Type": "application/json",
        }

        # Make the request
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{PANTHER_REST_API_URL}/rules/{rule_id}", headers=headers
            ) as response:
                if response.status == 404:
                    logger.warning(f"No rule found with ID: {rule_id}")
                    return {
                        "success": False,
                        "message": f"No rule found with ID: {rule_id}",
                    }
                elif response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Failed to fetch rule details: {error_text}")

                rule_data = await response.json()

        logger.info(f"Successfully retrieved rule details for ID: {rule_id}")

        # Format the response
        return {"success": True, "rule": rule_data}
    except Exception as e:
        logger.error(f"Failed to fetch rule details: {str(e)}")
        return {"success": False, "message": f"Failed to fetch rule details: {str(e)}"}


@mcp.resource("config://panther")
def get_panther_config() -> Dict[str, Any]:
    """Get the Panther API configuration"""
    return {
        "gql_api_url": PANTHER_GQL_API_URL,
        "rest_api_url": PANTHER_REST_API_URL,
        "authenticated": bool(os.getenv("PANTHER_API_KEY")),
        "server_name": MCP_SERVER_NAME,
        "tools": [
            "list_alerts",
            "get_alert_by_id",
            "list_sources",
            "execute_data_lake_query",
            "get_data_lake_query_results",
            "list_rules",
            "get_rule_by_id",
        ],
        "prompts": ["triage_alert", "prioritize_alerts"],
    }


async def main():
    """Main entry point for the MCP server."""
    try:
        logger.info("Starting Panther MCP server...")
        server = Server(mcp)
        async with stdio.stdio_server() as (read_stream, write_stream):
            logger.info("Server running with stdio transport")
            await server.run(
                read_stream,
                write_stream,
                initialization_options={"name": MCP_SERVER_NAME},
            )
    except Exception as e:
        logger.error(f"Server error: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    try:
        import asyncio

        logger.info("Starting server from command line...")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)
