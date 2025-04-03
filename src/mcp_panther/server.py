import logging
import os
import datetime
import sys
from typing import Dict, Any, Optional

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

UPDATE_ALERT_STATUS_MUTATION = gql("""
mutation UpdateAlertStatusById($input: UpdateAlertStatusByIdInput!) {
    updateAlertStatusById(input: $input) {
        alerts {
            id
            status
            updatedAt
        }
    }
}
""")

ADD_ALERT_COMMENT_MUTATION = gql("""
mutation CreateAlertComment($input: CreateAlertCommentInput!) {
    createAlertComment(input: $input) {
        comment {
            id
            body
            createdAt
            createdBy {
                ... on User {
                    id
                    email
                    givenName
                    familyName
                }
            }
            format
        }
    }
}
""")

UPDATE_ALERTS_ASSIGNEE_BY_ID_MUTATION = gql("""
mutation UpdateAlertsAssigneeById($input: UpdateAlertsAssigneeByIdInput!) {
    updateAlertsAssigneeById(input: $input) {
        alerts {
            id
            assignee {
                id
                email
                givenName
                familyName
            }
        }
    }
}
""")

LIST_USERS_QUERY = gql("""
query ListUsers {
    users {
        id
        email
        givenName
        familyName
        createdAt
        lastLoggedInAt
        status
        enabled
        role {
            id
            name
            permissions
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
    detection_id: str = None,
    event_count_max: int = None,
    event_count_min: int = None,
    log_sources: list[str] = None,
    log_types: list[str] = None,
    name_contains: str = None,
    page_size: int = 25,  # Default to 25, max is 50
    resource_types: list[str] = None,
    subtypes: list[str] = None,
    alert_type: str = "ALERT",  # Defaults to ALERT per schema
) -> Dict[str, Any]:
    """List alerts from Panther with comprehensive filtering options

    Args:
        start_date: Optional start date in ISO 8601 format (e.g. "2024-03-20T00:00:00Z")
        end_date: Optional end date in ISO 8601 format (e.g. "2024-03-21T00:00:00Z")
        severities: Optional list of severities to filter by (e.g. ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"])
        statuses: Optional list of statuses to filter by (e.g. ["OPEN", "TRIAGED", "RESOLVED", "CLOSED"])
        cursor: Optional cursor for pagination from a previous query
        detection_id: Optional detection ID to filter alerts by. If provided, date range is not required.
        event_count_max: Optional maximum number of events that returned alerts must have
        event_count_min: Optional minimum number of events that returned alerts must have
        log_sources: Optional list of log source IDs to filter alerts by
        log_types: Optional list of log type names to filter alerts by
        name_contains: Optional string to search for in alert titles
        page_size: Number of results per page (default: 25, maximum: 50)
        resource_types: Optional list of AWS resource type names to filter alerts by
        subtypes: Optional list of alert subtypes. Valid values depend on alert_type:
            - When alert_type="ALERT": ["POLICY", "RULE", "SCHEDULED_RULE"]
            - When alert_type="DETECTION_ERROR": ["RULE_ERROR", "SCHEDULED_RULE_ERROR"]
            - When alert_type="SYSTEM_ERROR": subtypes are not allowed
        alert_type: Type of alerts to return (default: "ALERT"). One of:
            - "ALERT": Regular detection alerts
            - "DETECTION_ERROR": Alerts from detection errors
            - "SYSTEM_ERROR": System error alerts
    """
    logger.info("Fetching alerts from Panther")

    try:
        client = _create_panther_client()

        # Validate page size
        if page_size < 1:
            raise ValueError("page_size must be greater than 0")
        if page_size > 50:
            logger.warning(
                f"page_size {page_size} exceeds maximum of 50, using 50 instead"
            )
            page_size = 50

        # Validate alert_type and subtypes combination
        valid_alert_types = ["ALERT", "DETECTION_ERROR", "SYSTEM_ERROR"]
        if alert_type not in valid_alert_types:
            raise ValueError(f"alert_type must be one of {valid_alert_types}")

        if subtypes:
            valid_subtypes = {
                "ALERT": ["POLICY", "RULE", "SCHEDULED_RULE"],
                "DETECTION_ERROR": ["RULE_ERROR", "SCHEDULED_RULE_ERROR"],
                "SYSTEM_ERROR": [],
            }
            if alert_type == "SYSTEM_ERROR":
                raise ValueError(
                    "subtypes are not allowed when alert_type is SYSTEM_ERROR"
                )

            allowed_subtypes = valid_subtypes[alert_type]
            invalid_subtypes = [st for st in subtypes if st not in allowed_subtypes]
            if invalid_subtypes:
                raise ValueError(
                    f"Invalid subtypes {invalid_subtypes} for alert_type={alert_type}. "
                    f"Valid subtypes are: {allowed_subtypes}"
                )

        # Prepare base input variables
        variables = {
            "input": {
                "pageSize": page_size,
                "sortBy": "createdAt",
                "sortDir": "descending",
                "type": alert_type,
            }
        }

        # Handle the required filter: either detectionId OR date range
        if detection_id:
            variables["input"]["detectionId"] = detection_id
            logger.info(f"Filtering by detection ID: {detection_id}")
        else:
            # If no detection_id, we must have a date range
            if not start_date or not end_date:
                start_date, end_date = _get_today_date_range()
                logger.info(
                    f"No detection ID and missing date range, using last 24 hours: {start_date} to {end_date}"
                )
            else:
                logger.info(f"Using provided date range: {start_date} to {end_date}")

            variables["input"]["createdAtAfter"] = start_date
            variables["input"]["createdAtBefore"] = end_date

        # Add optional filters
        if cursor:
            if not isinstance(cursor, str):
                raise ValueError(
                    "Cursor must be a string value from previous response's endCursor"
                )
            variables["input"]["cursor"] = cursor
            logger.info(f"Using cursor for pagination: {cursor}")

        if severities:
            variables["input"]["severities"] = severities
            logger.info(f"Filtering by severities: {severities}")

        if statuses:
            variables["input"]["statuses"] = statuses
            logger.info(f"Filtering by statuses: {statuses}")

        if event_count_max is not None:
            variables["input"]["eventCountMax"] = event_count_max
            logger.info(f"Filtering by max event count: {event_count_max}")

        if event_count_min is not None:
            variables["input"]["eventCountMin"] = event_count_min
            logger.info(f"Filtering by min event count: {event_count_min}")

        if log_sources:
            variables["input"]["logSources"] = log_sources
            logger.info(f"Filtering by log sources: {log_sources}")

        if log_types:
            variables["input"]["logTypes"] = log_types
            logger.info(f"Filtering by log types: {log_types}")

        if name_contains:
            variables["input"]["nameContains"] = name_contains
            logger.info(f"Filtering by name contains: {name_contains}")

        if resource_types:
            variables["input"]["resourceTypes"] = resource_types
            logger.info(f"Filtering by resource types: {resource_types}")

        if subtypes:
            variables["input"]["subtypes"] = subtypes
            logger.info(f"Filtering by subtypes: {subtypes}")

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
def prioritize_and_triage_alerts() -> str:
    return """You are an expert cyber security analyst. Your goal is to prioritize alerts based on severity, impact, and other relevant criteria to decide which alerts to investigate first. Use the following steps to prioritize alerts:
    1. List all alerts in the last 7 days excluding severities LOW, and logically group them by user, host, or other similar criteria. Alerts can be related even if they have different titles or log types (for example, if a user logs into Okta and then AWS).
    2. Triage each group of alerts to understand what happened and what the impact was. Query the data lake to read all associated events (database: panther_rule_matches.public, table: log type from the alert) and use the results to understand the impact.
    3. For each group, if the alerts are false positives, suggest a rule improvement by reading the Python source, comment on the alert with your analysis, and mark the alert as invalid. If the alerts are true positives, begin pivoting on the available data to understand the root cause and impact.
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


@mcp.tool()
async def update_alert_assignee_by_id(
    alert_ids: list[str], assignee_id: str
) -> Dict[str, Any]:
    """Update the assignee of one or more alerts through the assignee's ID.

    Args:
        alert_ids: List of alert IDs to update
        assignee_id: The ID of the user to assign the alerts to

    Returns:
        Dict containing:
        - success: Boolean indicating if the update was successful
        - alerts: List of updated alerts if successful
        - message: Error message if unsuccessful
    """
    logger.info(f"Updating assignee for alerts {alert_ids} to user {assignee_id}")

    try:
        # Prepare variables
        variables = {
            "input": {
                "ids": alert_ids,
                "assigneeId": assignee_id,
            }
        }

        # Execute mutation
        result = await _execute_query(UPDATE_ALERTS_ASSIGNEE_BY_ID_MUTATION, variables)

        if not result or "updateAlertsAssigneeById" not in result:
            raise Exception("Failed to update alert assignee")

        alerts_data = result["updateAlertsAssigneeById"]["alerts"]

        logger.info(f"Successfully updated assignee for alerts {alert_ids}")

        return {
            "success": True,
            "alerts": alerts_data,
        }

    except Exception as e:
        logger.error(f"Failed to update alert assignee: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to update alert assignee: {str(e)}",
        }


@mcp.tool()
async def list_panther_users() -> Dict[str, Any]:
    """List all Panther user accounts.

    Returns:
        Dict containing:
        - success: Boolean indicating if the query was successful
        - users: List of user accounts if successful
        - message: Error message if unsuccessful
    """
    logger.info("Fetching all Panther users")

    try:
        # Execute query
        result = await _execute_query(LIST_USERS_QUERY, {})

        if not result or "users" not in result:
            raise Exception("Failed to fetch users")

        users = result["users"]

        logger.info(f"Successfully retrieved {len(users)} users")

        return {
            "success": True,
            "users": users,
        }

    except Exception as e:
        logger.error(f"Failed to fetch users: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch users: {str(e)}",
        }


@mcp.resource("config://panther")
def get_panther_config() -> Dict[str, Any]:
    """Get the Panther configuration."""
    return {
        "gql_api_url": PANTHER_GQL_API_URL,
        "rest_api_url": PANTHER_REST_API_URL,
        "available_tools": [
            "list_alerts",
            "get_alert_by_id",
            "list_sources",
            "execute_data_lake_query",
            "get_data_lake_query_results",
            "list_rules",
            "get_rule_by_id",
            "create_rule",
            "put_rule",
            "disable_rule",
            "get_metrics_alerts_per_severity",
            "get_metrics_alerts_per_rule",
            "update_alert_status",
            "add_alert_comment",
            "update_alert_assignee_by_id",
            "list_panther_users",
        ],
        "available_resources": ["config://panther"],
        "available_prompts": ["triage_alert", "prioritize_alerts"],
    }


async def _execute_query(query: gql, variables: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a GraphQL query with the given variables.

    Args:
        query: The GraphQL query to execute
        variables: The variables to pass to the query

    Returns:
        The query result as a dictionary
    """
    client = _create_panther_client()
    async with client as session:
        return await session.execute(query, variable_values=variables)


@mcp.tool()
async def get_metrics_alerts_per_severity(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    interval_in_minutes: Optional[int] = 60,  # Default to 1 hour
) -> Dict[str, Any]:
    """Get metrics about alerts grouped by severity over time.

    Args:
        from_date: Optional start date in ISO 8601 format (e.g. "2024-03-20T00:00:00Z")
        to_date: Optional end date in ISO 8601 format (e.g. "2024-03-21T00:00:00Z")
        interval_in_minutes: Optional interval between metric checks (for plotting charts). Defaults to 60 minutes (1 hour).

    Returns:
        Dict containing:
        - alerts_per_severity: List of series with breakdown by severity
        - total_alerts: Total number of alerts in the period
    """
    try:
        # If no dates provided, get today's date range
        if not from_date and not to_date:
            from_date, to_date = _get_today_date_range()
            logger.info(
                f"No date range provided, using today's date range: {from_date} to {to_date}"
            )
        else:
            logger.info(f"Using provided date range: {from_date} to {to_date}")

        logger.info(
            f"Fetching alerts per severity metrics from {from_date} to {to_date}"
        )

        # Prepare the metrics query
        metrics_query = gql("""
            query Metrics($input: MetricsInput!) {
                metrics(input: $input) {
                    alertsPerSeverity {
                        label
                        value
                        breakdown
                    }
                    totalAlerts
                }
            }
        """)

        # Prepare variables
        variables = {
            "input": {
                "fromDate": from_date,
                "toDate": to_date,
                "intervalInMinutes": interval_in_minutes,
            }
        }

        # Execute query
        result = await _execute_query(metrics_query, variables)

        if not result or "metrics" not in result:
            raise Exception("Failed to fetch metrics data")

        metrics_data = result["metrics"]

        return {
            "success": True,
            "alerts_per_severity": metrics_data["alertsPerSeverity"],
            "total_alerts": metrics_data["totalAlerts"],
            "from_date": from_date,
            "to_date": to_date,
            "interval_in_minutes": interval_in_minutes,
        }

    except Exception as e:
        logger.error(f"Failed to fetch alerts per severity metrics: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch alerts per severity metrics: {str(e)}",
        }


@mcp.tool()
async def get_metrics_alerts_per_rule(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    interval_in_minutes: Optional[int] = 60,  # Default to 1 hour
) -> Dict[str, Any]:
    """Get metrics about alerts grouped by rule over time.

    Args:
        from_date: Optional start date in ISO 8601 format (e.g. "2024-03-20T00:00:00Z")
        to_date: Optional end date in ISO 8601 format (e.g. "2024-03-21T00:00:00Z")
        interval_in_minutes: Optional interval between metric checks (for plotting charts). Defaults to 60 minutes (1 hour).

    Returns:
        Dict containing:
        - alerts_per_rule: List of series with rule IDs and alert counts
        - total_alerts: Total number of alerts in the period
    """
    try:
        # If no dates provided, get today's date range
        if not from_date and not to_date:
            from_date, to_date = _get_today_date_range()
            logger.info(
                f"No date range provided, using today's date range: {from_date} to {to_date}"
            )
        else:
            logger.info(f"Using provided date range: {from_date} to {to_date}")

        logger.info(f"Fetching alerts per rule metrics from {from_date} to {to_date}")

        # Prepare the metrics query
        metrics_query = gql("""
            query Metrics($input: MetricsInput!) {
                metrics(input: $input) {
                    alertsPerRule {
                        entityId
                        label
                        value
                    }
                    totalAlerts
                }
            }
        """)

        # Prepare variables
        variables = {
            "input": {
                "fromDate": from_date,
                "toDate": to_date,
                "intervalInMinutes": interval_in_minutes,
            }
        }

        # Execute query
        result = await _execute_query(metrics_query, variables)

        if not result or "metrics" not in result:
            raise Exception("Failed to fetch metrics data")

        metrics_data = result["metrics"]

        return {
            "success": True,
            "alerts_per_rule": metrics_data["alertsPerRule"],
            "total_alerts": metrics_data["totalAlerts"],
            "from_date": from_date,
            "to_date": to_date,
            "interval_in_minutes": interval_in_minutes,
        }

    except Exception as e:
        logger.error(f"Failed to fetch alerts per rule metrics: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch alerts per rule metrics: {str(e)}",
        }


@mcp.tool()
async def update_alert_status(alert_ids: list[str], status: str) -> Dict[str, Any]:
    """Update the status of one or more Panther alerts.

    Args:
        alert_ids: List of alert IDs to update. Can be a single ID or multiple IDs.
        status: The new status for the alerts. Must be one of:
            - "OPEN": Alert is newly created and needs investigation
            - "TRIAGED": Alert is being investigated
            - "RESOLVED": Alert has been investigated and resolved
            - "CLOSED": Alert has been closed (no further action needed)

    Returns:
        Dict containing:
        - success: Boolean indicating if the update was successful
        - alerts: List of updated alerts if successful, each containing:
            - id: The alert ID
            - status: The new status
            - updatedAt: Timestamp of the update
        - message: Error message if unsuccessful

    Example:
        # Update a single alert
        result = await update_alert_status(["alert-123"], "TRIAGED")

        # Update multiple alerts
        result = await update_alert_status(["alert-123", "alert-456"], "RESOLVED")
    """
    logger.info(f"Updating status for alerts {alert_ids} to {status}")

    try:
        # Validate status
        valid_statuses = ["OPEN", "TRIAGED", "RESOLVED", "CLOSED"]
        if status not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")

        # Prepare variables
        variables = {
            "input": {
                "ids": alert_ids,
                "status": status,
            }
        }

        # Execute mutation
        result = await _execute_query(UPDATE_ALERT_STATUS_MUTATION, variables)

        if not result or "updateAlertStatusById" not in result:
            raise Exception("Failed to update alert status")

        alerts_data = result["updateAlertStatusById"]["alerts"]

        logger.info(f"Successfully updated {len(alerts_data)} alerts to status {status}")

        return {
            "success": True,
            "alerts": alerts_data,
        }

    except Exception as e:
        logger.error(f"Failed to update alert status: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to update alert status: {str(e)}",
        }


@mcp.tool()
async def add_alert_comment(alert_id: str, comment: str) -> Dict[str, Any]:
    """Add a comment to a Panther alert. Comments support Markdown formatting.

    Args:
        alert_id: The ID of the alert to comment on
        comment: The comment text to add

    Returns:
        Dict containing:
        - success: Boolean indicating if the comment was added successfully
        - comment: Created comment information if successful
        - message: Error message if unsuccessful
    """
    logger.info(f"Adding comment to alert {alert_id}")

    try:
        # Prepare variables
        variables = {
            "input": {
                "alertId": alert_id,
                "body": comment,
            }
        }

        # Execute mutation
        result = await _execute_query(ADD_ALERT_COMMENT_MUTATION, variables)

        if not result or "createAlertComment" not in result:
            raise Exception("Failed to add alert comment")

        comment_data = result["createAlertComment"]["comment"]

        logger.info(f"Successfully added comment to alert {alert_id}")

        return {
            "success": True,
            "comment": comment_data,
        }

    except Exception as e:
        logger.error(f"Failed to add alert comment: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to add alert comment: {str(e)}",
        }


@mcp.tool()
async def create_rule(
    rule_id: str,
    body: str,
    severity: str,
    description: str = None,
    display_name: str = None,
    enabled: bool = True,
    log_types: list[str] = None,
    dedup_period_minutes: int = 60,
    threshold: int = 1,
    runbook: str = None,
    tags: list[str] = None,
    summary_attributes: list[str] = None,
    inline_filters: str = None,
    reports: dict = None,
    tests: list[dict] = None,
    run_tests_first: bool = True,
) -> Dict[str, Any]:
    """Create a new Panther rule.

    Args:
        rule_id: Unique identifier for the rule
        body: Python code that implements the rule logic
        severity: Alert severity level (INFO, LOW, MEDIUM, HIGH, CRITICAL)
        description: Optional description of what the rule does
        display_name: Optional display name for the rule
        enabled: Whether the rule is active (default: True)
        log_types: Optional list of log types this rule applies to
        dedup_period_minutes: Time window for alert deduplication (default: 60)
        threshold: Number of events required to trigger alert (default: 1)
        runbook: Optional documentation on how to handle alerts
        tags: Optional list of tags for categorization
        summary_attributes: Optional list of fields to summarize in alerts
        inline_filters: Optional YAML filter for the rule
        reports: Optional mapping of report names to destinations
        tests: Optional list of unit tests for the rule
        run_tests_first: Whether to run tests before saving (default: True)

    Returns:
        Dict containing:
        - success: Boolean indicating if the creation was successful
        - rule: Created rule information if successful
        - message: Error message if unsuccessful
    """
    logger.info(f"Creating new rule with ID: {rule_id}")

    try:
        # Validate severity
        valid_severities = ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
        if severity not in valid_severities:
            raise ValueError(f"Severity must be one of {valid_severities}")

        # Prepare rule data
        rule_data = {
            "id": rule_id,
            "body": body,
            "severity": severity,
            "enabled": enabled,
            "dedupPeriodMinutes": dedup_period_minutes,
            "threshold": threshold,
        }

        # Add optional fields if provided
        if description:
            rule_data["description"] = description
        if display_name:
            rule_data["displayName"] = display_name
        if log_types:
            rule_data["logTypes"] = log_types
        if runbook:
            rule_data["runbook"] = runbook
        if tags:
            rule_data["tags"] = tags
        if summary_attributes:
            rule_data["summaryAttributes"] = summary_attributes
        if inline_filters:
            rule_data["inlineFilters"] = inline_filters
        if reports:
            rule_data["reports"] = reports
        if tests:
            rule_data["tests"] = tests

        # Prepare headers and query parameters
        headers = {
            "X-API-Key": get_panther_api_key(),
            "Content-Type": "application/json",
        }
        params = {"run-tests-first": str(run_tests_first).lower()}

        # Make the request
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{PANTHER_REST_API_URL}/rules",
                headers=headers,
                params=params,
                json=rule_data,
            ) as response:
                if response.status == 409:
                    return {
                        "success": False,
                        "message": "Rule with this ID already exists",
                    }
                elif response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Failed to create rule: {error_text}")

                result = await response.json()

        logger.info(f"Successfully created rule with ID: {rule_id}")

        return {
            "success": True,
            "rule": result,
        }

    except Exception as e:
        logger.error(f"Failed to create rule: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to create rule: {str(e)}",
        }


@mcp.tool()
async def put_rule(
    rule_id: str,
    body: str,
    severity: str,
    description: str = None,
    display_name: str = None,
    enabled: bool = None,
    log_types: list[str] = None,
    dedup_period_minutes: int = None,
    threshold: int = None,
    runbook: str = None,
    tags: list[str] = None,
    summary_attributes: list[str] = None,
    inline_filters: str = None,
    reports: dict = None,
    tests: list[dict] = None,
    run_tests_first: bool = True,
) -> Dict[str, Any]:
    """Update an existing Panther rule or create a new one if it doesn't exist.

    Args:
        rule_id: Unique identifier for the rule
        body: Python code that implements the rule logic
        severity: Alert severity level (INFO, LOW, MEDIUM, HIGH, CRITICAL)
        description: Optional description of what the rule does
        display_name: Optional display name for the rule
        enabled: Optional boolean to enable/disable the rule
        log_types: Optional list of log types this rule applies to
        dedup_period_minutes: Optional time window for alert deduplication
        threshold: Optional number of events required to trigger alert
        runbook: Optional documentation on how to handle alerts
        tags: Optional list of tags for categorization
        summary_attributes: Optional list of fields to summarize in alerts
        inline_filters: Optional YAML filter for the rule
        reports: Optional mapping of report names to destinations
        tests: Optional list of unit tests for the rule
        run_tests_first: Whether to run tests before saving (default: True)

    Returns:
        Dict containing:
        - success: Boolean indicating if the update was successful
        - rule: Updated rule information if successful
        - message: Error message if unsuccessful
    """
    logger.info(f"Updating rule with ID: {rule_id}")

    try:
        # Validate severity
        valid_severities = ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
        if severity not in valid_severities:
            raise ValueError(f"Severity must be one of {valid_severities}")

        # Prepare rule data
        rule_data = {
            "id": rule_id,
            "body": body,
            "severity": severity,
        }

        # Add optional fields if provided
        if enabled is not None:
            rule_data["enabled"] = enabled
        if description:
            rule_data["description"] = description
        if display_name:
            rule_data["displayName"] = display_name
        if log_types:
            rule_data["logTypes"] = log_types
        if dedup_period_minutes:
            rule_data["dedupPeriodMinutes"] = dedup_period_minutes
        if threshold:
            rule_data["threshold"] = threshold
        if runbook:
            rule_data["runbook"] = runbook
        if tags:
            rule_data["tags"] = tags
        if summary_attributes:
            rule_data["summaryAttributes"] = summary_attributes
        if inline_filters:
            rule_data["inlineFilters"] = inline_filters
        if reports:
            rule_data["reports"] = reports
        if tests:
            rule_data["tests"] = tests

        # Prepare headers and query parameters
        headers = {
            "X-API-Key": get_panther_api_key(),
            "Content-Type": "application/json",
        }
        params = {"run-tests-first": str(run_tests_first).lower()}

        # Make the request
        async with aiohttp.ClientSession() as session:
            async with session.put(
                f"{PANTHER_REST_API_URL}/rules/{rule_id}",
                headers=headers,
                params=params,
                json=rule_data,
            ) as response:
                if response.status not in [200, 201]:
                    error_text = await response.text()
                    raise Exception(f"Failed to update rule: {error_text}")

                result = await response.json()

        logger.info(f"Successfully updated rule with ID: {rule_id}")

        return {
            "success": True,
            "rule": result,
        }

    except Exception as e:
        logger.error(f"Failed to update rule: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to update rule: {str(e)}",
        }


@mcp.tool()
async def disable_rule(rule_id: str) -> Dict[str, Any]:
    """Disable a Panther rule by setting enabled to false.

    Args:
        rule_id: The ID of the rule to disable

    Returns:
        Dict containing:
        - success: Boolean indicating if the update was successful
        - rule: Updated rule information if successful
        - message: Error message if unsuccessful
    """
    logger.info(f"Disabling rule with ID: {rule_id}")

    try:
        # First get the current rule to preserve other fields
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{PANTHER_REST_API_URL}/rules/{rule_id}",
                headers={"X-API-Key": get_panther_api_key()},
            ) as response:
                if response.status == 404:
                    return {
                        "success": False,
                        "message": f"Rule with ID {rule_id} not found",
                    }
                elif response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Failed to fetch rule: {error_text}")

                rule_data = await response.json()

        # Update only the enabled field
        rule_data["enabled"] = False

        # Prepare headers and query parameters
        headers = {
            "X-API-Key": get_panther_api_key(),
            "Content-Type": "application/json",
        }
        params = {"run-tests-first": "false"}  # Skip tests for simple disable

        # Make the update request
        async with aiohttp.ClientSession() as session:
            async with session.put(
                f"{PANTHER_REST_API_URL}/rules/{rule_id}",
                headers=headers,
                params=params,
                json=rule_data,
            ) as response:
                if response.status not in [200, 201]:
                    error_text = await response.text()
                    raise Exception(f"Failed to disable rule: {error_text}")

                result = await response.json()

        logger.info(f"Successfully disabled rule with ID: {rule_id}")

        return {
            "success": True,
            "rule": result,
        }

    except Exception as e:
        logger.error(f"Failed to disable rule: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to disable rule: {str(e)}",
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
