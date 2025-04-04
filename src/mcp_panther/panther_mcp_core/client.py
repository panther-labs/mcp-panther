import os
import logging
import datetime
from typing import Dict, Any, Tuple

from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

# GraphQL endpoint for Panther
PANTHER_GQL_API_URL = os.getenv(
    "PANTHER_GQL_API_URL", "https://api.runpanther.com/public/graphql"
)

# REST API endpoints for Panther
PANTHER_REST_API_URL = os.getenv("PANTHER_REST_API_URL", "https://api.runpanther.com")

# Get logger
logger = logging.getLogger("mcp-panther")


def get_panther_api_key() -> str:
    """Get Panther API key from environment variable"""
    api_key = os.getenv("PANTHER_API_KEY")
    if not api_key:
        raise ValueError("PANTHER_API_KEY environment variable is not set")
    return api_key


def _create_panther_client() -> Client:
    """Create a Panther GraphQL client with proper configuration"""
    transport = AIOHTTPTransport(
        url=PANTHER_GQL_API_URL,
        headers={"X-API-Key": get_panther_api_key()},
        ssl=True,  # Enable SSL verification
    )
    return Client(transport=transport, fetch_schema_from_transport=True)


def _get_today_date_range() -> Tuple[str, str]:
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
