import datetime
import json
import logging
import os
import re
from importlib.metadata import version
from typing import Any, AnyStr, Dict, List, Optional, Tuple, Union

import aiohttp
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

PACKAGE_NAME = "mcp-panther"

# Get logger
logger = logging.getLogger(PACKAGE_NAME)


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
        except UnexpectedResponseStatusError:
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


async def _create_panther_client() -> Client:
    """Create a Panther GraphQL client with proper configuration"""
    transport = AIOHTTPTransport(
        url=await get_panther_gql_endpoint(),
        headers={
            "X-API-Key": get_panther_api_key(),
            "User-Agent": _get_user_agent(),
        },
        ssl=True,  # Enable SSL verification
    )
    return Client(transport=transport, fetch_schema_from_transport=True)


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


def get_today_date_range() -> Tuple[datetime.datetime, datetime.datetime]:
    """Get date range for the last 24 hours (UTC)"""
    # Get current UTC time and shift back by one day since we're already in tomorrow
    now = datetime.datetime.now(datetime.timezone.utc)
    now = now - datetime.timedelta(days=1)

    # Get start of today (midnight UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Get end of today (midnight UTC of next day)
    today_end = today_start + datetime.timedelta(days=1)

    logger.debug(f"Calculated date range - Start: {today_start}, End: {today_end}")
    return today_start, today_end


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
    client = await _create_panther_client()
    async with client as session:
        return await session.execute(query, variable_values=variables)


class PantherRestClient:
    """A client for making REST API calls to Panther's API.

    This client handles session management, URL construction, and default headers.
    It uses aiohttp for making async HTTP requests.
    """

    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        self._base_url: Optional[str] = None
        self._headers: Optional[Dict[str, str]] = None

    async def __aenter__(self) -> "PantherRestClient":
        """Set up the client session when entering an async context."""
        if not self._session:
            self._session = aiohttp.ClientSession()
            self._base_url = await get_panther_rest_api_base()
            self._headers = {
                "X-API-Key": get_panther_api_key(),
                "Content-Type": "application/json",
                "User-Agent": _get_user_agent(),
            }
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up the client session when exiting an async context."""
        if self._session:
            await self._session.close()
            self._session = None

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
