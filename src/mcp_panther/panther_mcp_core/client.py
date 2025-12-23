import asyncio
import datetime
import json
import logging
import os
import re
from contextlib import asynccontextmanager
from importlib.metadata import version
from typing import Any, AnyStr, Dict, List, Optional, Tuple, Union

import aiohttp
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.exceptions import TransportQueryError

PACKAGE_NAME = "mcp-panther"

# Get logger
logger = logging.getLogger(PACKAGE_NAME)

# Module-level client storage (managed by lifespan context)
_graphql_client: Optional[Client] = None
_graphql_transport: Optional[AIOHTTPTransport] = None
_graphql_connector: Optional[aiohttp.TCPConnector] = (
    None  # Shared connection pool for GraphQL
)
_graphql_session: Optional[aiohttp.ClientSession] = (
    None  # GQL session for concurrent GraphQL requests
)

# REST API client storage
_rest_client: Optional["PantherRestClient"] = None
_rest_session: Optional[aiohttp.ClientSession] = (
    None  # Persistent session for REST API requests
)
_rest_connector: Optional[aiohttp.TCPConnector] = (
    None  # Shared connection pool for REST
)


class UnexpectedResponseStatusError(ValueError):
    pass


async def get_json_from_script_tag(
    url: str, script_id: str
) -> Optional[Union[Dict[str, Any], AnyStr]]:
    """
    Extract JSON content from a script tag with the specified ID using aiohttp.

    Args:
        url: The URL to fetch
        script_id: The ID of the script tag containing JSON

    Returns:
        Parsed JSON content, raw string if not valid JSON, or None if not found
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(
            url, ssl=not os.getenv("PANTHER_ALLOW_INSECURE_INSTANCE")
        ) as response:
            if response.status != 200:
                raise UnexpectedResponseStatusError(
                    f"unexpected status code when resolving api info: {response.status}"
                )

            html_content: str = await response.text()

    # Pattern to match script tag with specific ID and capture its content
    pattern: str = f"<script[^>]*id=[\"']{script_id}[\"'][^>]*>(.*?)</script>"
    match: Optional[re.Match] = re.search(pattern, html_content, re.DOTALL)

    if match:
        json_str: AnyStr = match.group(1).strip()
        return json.loads(json_str)

    raise ValueError("could not find json info")


def get_panther_api_key() -> str:
    """Get Panther API key from environment variable"""
    api_key = os.getenv("PANTHER_API_TOKEN")
    if not api_key:
        raise ValueError("PANTHER_API_TOKEN environment variable is not set")
    return api_key


def get_panther_instance_url() -> str:
    """Get the Panther instance URL from environment variable.

    Returns:
        str: The Panther instance URL from PANTHER_INSTANCE_URL environment variable
    """
    result = os.getenv("PANTHER_INSTANCE_URL")
    if not result:
        raise ValueError("PANTHER_INSTANCE_URL environment not set")

    return result


instance_config: Optional[Dict[str, Any]] = None


async def get_instance_config() -> Optional[Dict[str, Any]]:
    """Retrieve and cache the Panther instance configuration from the instance URL.

    Returns:
        Optional[Dict[str, Any]]: The Panther instance configuration dictionary if successful,
                                 None if the instance URL is not set or configuration cannot be fetched.
    """
    global instance_config
    instance_url = get_panther_instance_url()
    if instance_config is None:
        try:
            info = await get_json_from_script_tag(instance_url, "__PANTHER_CONFIG__")
            instance_config = info
        except (UnexpectedResponseStatusError, ValueError):
            # Fallback: derive config from URL if script tag not found
            if "public/graphql" in instance_url:
                instance_config = {
                    "rest": instance_url.replace("public/graphql", "").strip("/")
                }
            else:
                instance_config = {
                    "rest": instance_url.strip("/"),
                }

    return instance_config


async def get_panther_rest_api_base() -> str:
    """Get the base URL for Panther's REST API.

    This function first checks for a REST API URL in environment variables.
    If not found, it attempts to derive it from the instance configuration.

    Returns:
        str: The base URL for Panther's REST API endpoints.
             Returns an empty string if neither environment variable is set
             nor instance configuration is available.
    """
    base = os.getenv("PANTHER_REST_API_URL")
    if base:
        return base
    config = await get_instance_config()
    if not config:
        return ""
    if config.get("rest"):
        return config.get("rest")

    base = config.get("WEB_APPLICATION_GRAPHQL_API_ENDPOINT", "")
    return base.replace("/internal/graphql", "")


async def get_panther_gql_endpoint() -> str:
    """Get the GraphQL endpoint URL for Panther's API.

    This function first checks for a GraphQL API URL in environment variables.
    If not found, it attempts to construct it from the REST API base URL.

    Returns:
        str: The complete URL for Panther's GraphQL endpoint.
             Returns an empty string if neither environment variable is set
             nor REST API base URL can be determined.
    """
    base = os.getenv("PANTHER_GQL_API_URL")
    if base:
        return base
    base = await get_panther_rest_api_base()
    if not base:
        return ""

    return base + "/public/graphql"


def _is_running_in_docker() -> bool:
    """Check if the process is running inside a Docker container.

    Returns:
        bool: True if running in Docker, False otherwise
    """
    return os.environ.get("MCP_PANTHER_DOCKER_RUNTIME") == "true"


def _get_user_agent() -> str:
    """Get the user agent string for API requests.

    Returns:
        str: User agent string in format '{PACKAGE_NAME}/{version} (Python)' or '{PACKAGE_NAME}/{version} (Python; Docker)'
    """
    try:
        package_version = version(PACKAGE_NAME)
        base_agent = f"{PACKAGE_NAME}/{package_version}"
    except Exception as e:
        logger.debug(f"Failed to get package version: {e}")
        base_agent = f"{PACKAGE_NAME}/development"

    env_info = ["Python"]
    if _is_running_in_docker():
        env_info.append("Docker")

    return f"{base_agent} ({'; '.join(env_info)})"


@asynccontextmanager
async def lifespan(mcp):
    """Manage server lifecycle and shared HTTP resources.

    This context manager creates shared HTTP clients for the GraphQL API
    that persist across requests, enabling proper connection pooling and
    preventing "Connector is closed" errors during parallel tool calls.

    If credentials are not configured, the server will still start but tools
    will fail with clear error messages when they attempt API calls.

    Args:
        mcp: The FastMCP server instance

    Yields:
        dict: Shared resources (graphql_client, transport, connector)
    """
    global _graphql_client, _graphql_transport, _graphql_connector, _graphql_session
    global _rest_session, _rest_connector

    logger.info("Initializing shared HTTP clients for Panther API")

    # Check if credentials are available
    instance_url = os.getenv("PANTHER_INSTANCE_URL")
    api_token = os.getenv("PANTHER_API_TOKEN")

    if not instance_url or not api_token:
        logger.warning(
            "Panther credentials not configured. "
            "Set PANTHER_INSTANCE_URL and PANTHER_API_TOKEN environment variables. "
            "Tools will fail when attempting API calls."
        )
        # Yield without initializing clients - tools will fail gracefully at call time
        yield {}
        return

    try:
        # Create persistent connection pools for all requests
        # High limits to support parallel requests from Claude Code

        # GraphQL connection pool
        _graphql_connector = aiohttp.TCPConnector(
            limit=100,  # Total connection pool size
            limit_per_host=50,  # Connections per host (Panther API)
            ttl_dns_cache=300,  # DNS cache TTL in seconds
        )

        # REST API connection pool
        _rest_connector = aiohttp.TCPConnector(
            limit=100,  # Total connection pool size
            limit_per_host=50,  # Connections per host (Panther API)
            ttl_dns_cache=300,  # DNS cache TTL in seconds
        )

        # Create GraphQL transport with connection pool
        # Using client_session_args because that's what AIOHTTPTransport accepts
        _graphql_transport = AIOHTTPTransport(
            url=await get_panther_gql_endpoint(),
            headers={
                "X-API-Key": get_panther_api_key(),
                "User-Agent": _get_user_agent(),
            },
            ssl=True,  # Enable SSL verification
            timeout=60,  # 60 second timeout for queries
            client_session_args={
                "connector": _graphql_connector,
                "connector_owner": False,  # We manage connector lifecycle
            },
        )

        # Create GraphQL client with the transport
        _graphql_client = Client(
            transport=_graphql_transport,
            fetch_schema_from_transport=True,
            execute_timeout=60,
        )

        # Create a persistent GQL session for concurrent GraphQL requests
        # This session stays open for the server lifetime
        async with _graphql_client as _graphql_session:
            logger.info("GraphQL session opened - ready for concurrent requests")

            # Create persistent REST API session
            _rest_session = aiohttp.ClientSession(
                connector=_rest_connector,
                connector_owner=False,  # We manage connector lifecycle
            )
            logger.info("REST session opened - ready for concurrent requests")

            # Server runs here with persistent sessions
            yield {
                "graphql_client": _graphql_client,
                "graphql_session": _graphql_session,
                "graphql_transport": _graphql_transport,
                "graphql_connector": _graphql_connector,
                "rest_session": _rest_session,
                "rest_connector": _rest_connector,
            }

        logger.info("Server shutdown - cleaning up GraphQL resources")

    finally:
        # Cleanup on shutdown
        # The GQL session is closed by the async context manager above
        logger.info("Shutting down shared HTTP clients")

        _graphql_session = None
        _graphql_client = None

        # Close REST session
        if _rest_session:
            try:
                await _rest_session.close()
                logger.debug("REST session closed successfully")
            except Exception as e:
                logger.error(f"Error closing REST session: {e}")
            finally:
                _rest_session = None

        # Close GraphQL transport
        if _graphql_transport:
            try:
                await _graphql_transport.close()
                logger.debug("GraphQL transport closed successfully")
            except Exception as e:
                logger.error(f"Error closing GraphQL transport: {e}")
            finally:
                _graphql_transport = None

        # Close connectors since we own them (connector_owner=False)
        if _rest_connector:
            try:
                await _rest_connector.close()
                logger.debug("REST connector closed successfully")
            except Exception as e:
                logger.error(f"Error closing REST connector: {e}")
            finally:
                _rest_connector = None

        if _graphql_connector:
            try:
                await _graphql_connector.close()
                # Give connections time to close gracefully
                await asyncio.sleep(0.25)
                logger.debug("GraphQL connector closed successfully")
            except Exception as e:
                logger.error(f"Error closing GraphQL connector: {e}")
            finally:
                _graphql_connector = None

        logger.info("HTTP clients shutdown complete")


def graphql_date_format(input_date: datetime) -> str:
    """Format a datetime object for GraphQL queries.

    Before: 2025-05-20 00:00:00+00:00
    After: 2025-05-20T00:00:00.000Z

    Args:
        input_date: The datetime object to format

    Returns:
        The formatted date string
    """
    return input_date.isoformat(timespec="milliseconds").replace("+00:00", "Z")


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


def _get_week_date_range() -> Tuple[str, str]:
    """Get date range for the last 7 days (UTC) from current time"""
    utc_now = datetime.datetime.now(datetime.timezone.utc)

    # Get 7 days ago, rounded down to start of hour for consistent inputs
    created_after = utc_now - datetime.timedelta(days=7)
    created_after = created_after.replace(minute=0, second=0, microsecond=0)

    # Get current time rounded up to end of hour
    created_before = utc_now.replace(minute=59, second=59, microsecond=0)

    # Format for GraphQL query (ISO 8601 with milliseconds and Z suffix)
    created_after = created_after.isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )
    created_before = created_before.isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )

    logger.debug(
        f"Calculated week range - Start: {created_after}, End: {created_before}"
    )
    return created_after, created_before


async def _execute_query(query: gql, variables: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a GraphQL query using the persistent GQL session.

    This function uses the module-level persistent GQL session that is created
    during server lifespan and stays open for concurrent requests. Using the session
    pattern (async with client as session) is the GQL library's recommended approach
    for handling concurrent queries safely.

    Args:
        query: The GraphQL query to execute
        variables: The variables to pass to the query

    Returns:
        The query result as a dictionary

    Raises:
        RuntimeError: If the shared GraphQL session is not initialized
        TransportQueryError: If the GraphQL query fails
    """
    global _graphql_session

    if _graphql_session is None:
        raise RuntimeError(
            "GraphQL session not initialized. "
            "Server must be started with lifespan context and valid Panther credentials. "
            "Set PANTHER_INSTANCE_URL and PANTHER_API_TOKEN environment variables."
        )

    try:
        # Use the persistent session which is safe for concurrent requests
        result = await _graphql_session.execute(query, variable_values=variables)
        return result

    except TransportQueryError as e:
        logger.error(f"GraphQL query failed: {e}")
        raise
    except Exception as e:
        # Check if it's a connection error
        if "Connector is closed" in str(e):
            logger.error(
                f"Connection pool error detected: {e}. "
                f"This should not happen with persistent session - please report this issue."
            )
        raise


class PantherRestClient:
    """A client for making REST API calls to Panther's API.

    This client uses the persistent session created in the lifespan context
    to handle concurrent requests from Claude Code without "Connector is closed" errors.
    """

    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        self._base_url: Optional[str] = None
        self._headers: Optional[Dict[str, str]] = None

    async def __aenter__(self) -> "PantherRestClient":
        """Set up the client to use the persistent session."""
        global _rest_session

        if _rest_session is None:
            raise RuntimeError(
                "REST session not initialized. "
                "Server must be started with lifespan context."
            )

        # Use the persistent session from lifespan
        self._session = _rest_session
        self._base_url = await get_panther_rest_api_base()
        self._headers = {
            "X-API-Key": get_panther_api_key(),
            "Content-Type": "application/json",
            "User-Agent": _get_user_agent(),
        }
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up without closing the persistent session."""
        # Don't close the persistent session - it's managed by lifespan
        # Just clear the reference
        self._session = None
        self._base_url = None
        self._headers = None

    def _build_url(self, path: str) -> str:
        """Construct the full URL for a given path.

        Args:
            path: The API path (e.g., '/rules' or '/rules/{rule_id}')

        Returns:
            str: The complete URL with base URL and path
        """
        # Remove leading slash if present to avoid double slashes
        if path.startswith("/"):
            path = path[1:]
        return f"{self._base_url}/{path}"

    async def _validate_response(
        self, response: aiohttp.ClientResponse, expected_codes: List[int]
    ) -> None:
        """Validate the response status code against expected codes.

        Args:
            response: The aiohttp ClientResponse object
            expected_codes: List of acceptable status codes

        Raises:
            Exception: If the status code is not in the expected codes
        """
        if response.status not in expected_codes:
            error_text = await response.text() if response.status >= 400 else ""
            if response.status == 401:
                raise Exception(
                    f"Invalid API Key Detected. Please notify user that their API Key is invalid. STOP and wait for user to fix the issue. error: {error_text}"
                )
            raise Exception(f"Request failed (HTTP {response.status}): {error_text}")

    async def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        expected_codes: List[int] = [200],
    ) -> Tuple[Dict[str, Any], int]:
        """Make a GET request to the Panther API.

        Args:
            path: The API path (e.g., '/rules' or '/rules/{rule_id}')
            params: Optional query parameters
            expected_codes: List of status codes considered successful (default: [200])

        Returns:
            Tuple[Dict[str, Any], int]: A tuple containing:
                - The JSON response from the API
                - The HTTP status code

        Raises:
            Exception: If the request fails or returns an unexpected status code
        """
        if not self._session:
            raise RuntimeError("Client must be used within an async context manager")

        async with self._session.get(
            self._build_url(path),
            headers=self._headers,
            params=params,
            ssl=not os.getenv("PANTHER_ALLOW_INSECURE_INSTANCE"),
        ) as response:
            await self._validate_response(response, expected_codes)
            return await response.json(), response.status

    async def post(
        self,
        path: str,
        json_data: Dict[str, Any],
        params: Optional[Dict[str, Any]] = None,
        expected_codes: List[int] = [200, 201],
    ) -> Tuple[Dict[str, Any], int]:
        """Make a POST request to the Panther API.

        Args:
            path: The API path (e.g., '/rules')
            json_data: The JSON data to send in the request body
            params: Optional query parameters
            expected_codes: List of status codes considered successful (default: [200, 201])

        Returns:
            Tuple[Dict[str, Any], int]: A tuple containing:
                - The JSON response from the API
                - The HTTP status code

        Raises:
            Exception: If the request fails or returns an unexpected status code
        """
        if not self._session:
            raise RuntimeError("Client must be used within an async context manager")

        async with self._session.post(
            self._build_url(path),
            headers=self._headers,
            json=json_data,
            params=params,
            ssl=not os.getenv("PANTHER_ALLOW_INSECURE_INSTANCE"),
        ) as response:
            await self._validate_response(response, expected_codes)
            return await response.json(), response.status

    async def put(
        self,
        path: str,
        json_data: Dict[str, Any],
        params: Optional[Dict[str, Any]] = None,
        expected_codes: List[int] = [200, 201],
    ) -> Tuple[Dict[str, Any], int]:
        """Make a PUT request to the Panther API.

        Args:
            path: The API path (e.g., '/rules/{rule_id}')
            json_data: The JSON data to send in the request body
            params: Optional query parameters
            expected_codes: List of status codes considered successful (default: [200, 201])

        Returns:
            Tuple[Dict[str, Any], int]: A tuple containing:
                - The JSON response from the API
                - The HTTP status code

        Raises:
            Exception: If the request fails or returns an unexpected status code
        """
        if not self._session:
            raise RuntimeError("Client must be used within an async context manager")

        async with self._session.put(
            self._build_url(path),
            headers=self._headers,
            json=json_data,
            params=params,
            ssl=not os.getenv("PANTHER_ALLOW_INSECURE_INSTANCE"),
        ) as response:
            await self._validate_response(response, expected_codes)
            return await response.json(), response.status

    async def patch(
        self,
        path: str,
        json_data: Dict[str, Any],
        params: Optional[Dict[str, Any]] = None,
        expected_codes: List[int] = [200, 201],
    ) -> Tuple[Dict[str, Any], int]:
        """Make a PATCH request to the Panther API.

        Args:
            path: The API path (e.g., '/rules/{rule_id}')
            json_data: The JSON data to send in the request body
            params: Optional query parameters
            expected_codes: List of status codes considered successful (default: [200, 201])

        Returns:
            Tuple[Dict[str, Any], int]: A tuple containing:
                - The JSON response from the API
                - The HTTP status code

        Raises:
            Exception: If the request fails or returns an unexpected status code
        """
        if not self._session:
            raise RuntimeError("Client must be used within an async context manager")

        async with self._session.patch(
            self._build_url(path),
            headers=self._headers,
            json=json_data,
            params=params,
            ssl=not os.getenv("PANTHER_ALLOW_INSECURE_INSTANCE"),
        ) as response:
            await self._validate_response(response, expected_codes)
            return await response.json(), response.status

    async def delete(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        expected_codes: List[int] = [200],
    ) -> Tuple[Dict[str, Any], int]:
        """Make a DELETE request to the Panther API.

        Args:
            path: The API path (e.g., '/rules/{rule_id}')
            params: Optional query parameters
            expected_codes: List of status codes considered successful (default: [200])

        Returns:
            Tuple[Dict[str, Any], int]: A tuple containing:
                - The JSON response from the API
                - The HTTP status code

        Raises:
            Exception: If the request fails or returns an unexpected status code
        """
        if not self._session:
            raise RuntimeError("Client must be used within an async context manager")

        async with self._session.delete(
            self._build_url(path),
            headers=self._headers,
            params=params,
            ssl=not os.getenv("PANTHER_ALLOW_INSECURE_INSTANCE"),
        ) as response:
            await self._validate_response(response, expected_codes)
            return await response.json(), response.status


_rest_client: Optional[PantherRestClient] = None


def get_rest_client() -> PantherRestClient:
    """Get the singleton instance of PantherRestClient.

    This function lazily instantiates the client on first call
    and returns the same instance for subsequent calls.

    Returns:
        PantherRestClient: The singleton instance of the REST client
    """
    global _rest_client
    if _rest_client is None:
        _rest_client = PantherRestClient()
    return _rest_client
