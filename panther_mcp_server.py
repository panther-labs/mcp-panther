import logging
import os
import datetime
from typing import Dict, Any, Optional

from dotenv import load_dotenv
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from mcp.server.fastmcp import FastMCP

# Server name
MCP_SERVER_NAME = "panther-mcp"

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(MCP_SERVER_NAME)

# Load environment variables from .env file if it exists
load_dotenv()

# Server dependencies
deps = [
    "python-dotenv",
    "gql[aiohttp]",
    "aiohttp",
    "uvicorn",
]

# Create the MCP server
mcp = FastMCP(MCP_SERVER_NAME, dependencies=deps)

# GraphQL endpoint for Panther
PANTHER_API_URL = os.getenv("PANTHER_API_URL", "https://api.runpanther.com/public/graphql")

# Get Panther API key from environment variable
def get_panther_api_key() -> str:
    api_key = os.getenv("PANTHER_API_KEY")
    if not api_key:
        raise ValueError("PANTHER_API_KEY environment variable is not set")
    return api_key

# GraphQL queries
AUTHENTICATE_QUERY = gql("""
query AlertDetails {
    alert(id: "FAKE_ALERT_ID") {
        id
        title
        severity
        status
    }
}
""")

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

def _get_today_date_range() -> tuple:
    """Get date range for today (UTC)"""
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
        url=PANTHER_API_URL,
        headers={"X-API-Key": get_panther_api_key()},
        ssl=True  # Enable SSL verification
    )
    return Client(transport=transport, fetch_schema_from_transport=True)

@mcp.tool()
async def authenticate_with_panther() -> Dict[str, Any]:
    """Test authentication with Panther using the API key"""
    logger.info("Testing authentication with Panther")
    try:
        client = _create_panther_client()
        
        # Execute the query asynchronously
        async with client as session:
            await session.execute(AUTHENTICATE_QUERY)
            
        logger.info("Successfully authenticated with Panther")
        return {"success": True, "message": "Authentication successful"}
    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}")
        return {"success": False, "message": f"Authentication failed: {str(e)}"}

@mcp.tool()
async def get_todays_alerts() -> Dict[str, Any]:
    """Get alerts from Panther for the current day"""
    logger.info("Fetching today's alerts from Panther")
    try:
        client = _create_panther_client()
        
        # Get today's date range
        start_date, end_date = _get_today_date_range()
        logger.info(f"Querying alerts between {start_date} and {end_date}")
        
        # Prepare input variables
        variables = {
            "input": {
                "createdAtAfter": start_date,
                "createdAtBefore": end_date,
                "pageSize": 25,  # Default page size
                "sortBy": "createdAt",  # Sort by creation date
                "sortDir": "descending"  # Most recent first
            }
        }
        logger.debug(f"Query variables: {variables}")
        
        # Execute the query asynchronously
        async with client as session:
            result = await session.execute(GET_TODAYS_ALERTS_QUERY, variable_values=variables)
        
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
            "start_cursor": page_info.get("startCursor")
        }
    except Exception as e:
        logger.error(f"Failed to fetch alerts: {str(e)}")
        return {"success": False, "message": f"Failed to fetch alerts: {str(e)}"}

@mcp.tool()
async def get_alerts_with_cursor(cursor: str) -> Dict[str, Any]:
    """Get next page of alerts using a cursor from a previous query"""
    logger.info(f"Fetching alerts with cursor: {cursor}")
    try:
        client = _create_panther_client()
        
        # Get today's date range
        start_date, end_date = _get_today_date_range()
        
        # Prepare input variables
        variables = {
            "input": {
                "createdAtAfter": start_date,
                "createdAtBefore": end_date,
                "cursor": cursor
            }
        }
        
        # Execute the query asynchronously
        async with client as session:
            result = await session.execute(GET_TODAYS_ALERTS_QUERY, variable_values=variables)
        
        # Process results
        alerts_data = result.get("alerts", {})
        alert_edges = alerts_data.get("edges", [])
        page_info = alerts_data.get("pageInfo", {})
        
        # Extract alerts from edges
        alerts = [edge["node"] for edge in alert_edges]
        
        logger.info(f"Successfully retrieved {len(alerts)} alerts with cursor")
        
        # Format the response
        return {
            "success": True,
            "alerts": alerts,
            "total_alerts": len(alerts),
            "has_next_page": page_info.get("hasNextPage", False),
            "end_cursor": page_info.get("endCursor")
        }
    except Exception as e:
        logger.error(f"Failed to fetch alerts with cursor: {str(e)}")
        return {"success": False, "message": f"Failed to fetch alerts with cursor: {str(e)}"}

@mcp.tool()
async def get_alert_by_id(alert_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific alert by ID"""
    logger.info(f"Fetching alert details for ID: {alert_id}")
    try:
        client = _create_panther_client()
                
        # Prepare input variables
        variables = {
            "id": alert_id
        }
        
        # Execute the query asynchronously
        async with client as session:
            result = await session.execute(GET_ALERT_BY_ID_QUERY, variable_values=variables)
        
        # Get alert data
        alert_data = result.get("alert", {})
        
        if not alert_data:
            logger.warning(f"No alert found with ID: {alert_id}")
            return {
                "success": False,
                "message": f"No alert found with ID: {alert_id}"
            }
        
        logger.info(f"Successfully retrieved alert details for ID: {alert_id}")
        
        # Format the response
        return {
            "success": True,
            "alert": alert_data
        }
    except Exception as e:
        logger.error(f"Failed to fetch alert details: {str(e)}")
        return {"success": False, "message": f"Failed to fetch alert details: {str(e)}"}

@mcp.resource("config://panther")
def get_panther_config() -> Dict[str, Any]:
    """Get the Panther API configuration"""
    return {
        "api_url": PANTHER_API_URL,
        "authenticated": bool(os.getenv("PANTHER_API_KEY")),
        "server_name": MCP_SERVER_NAME,
        "tools": [
            "authenticate_with_panther",
            "get_todays_alerts",
            "get_alerts_with_cursor",
            "get_alert_by_id"
        ]
    }
