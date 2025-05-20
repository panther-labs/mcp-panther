import os
from unittest import mock

import pytest
from aiohttp import ClientResponse

from mcp_panther.panther_mcp_core.client import (
    UnexpectedResponseStatusError,
    _get_user_agent,
    _is_running_in_docker,
    get_instance_config,
    get_json_from_script_tag,
    get_panther_rest_api_base,
)


@pytest.mark.parametrize(
    "env_value,expected",
    [
        ("true", True),
        ("false", False),
        (None, False),
        ("", False),
    ],
)
def test_is_running_in_docker(env_value, expected):
    """Test Docker environment detection with various environment variable values."""
    with mock.patch.dict(
        os.environ,
        {"MCP_PANTHER_DOCKER_RUNTIME": env_value} if env_value is not None else {},
    ):
        assert _is_running_in_docker() == expected


@pytest.mark.parametrize(
    "docker_running,version,expected",
    [
        (True, "1.0.0", "mcp-panther/1.0.0 (Python; Docker)"),
        (False, "1.0.0", "mcp-panther/1.0.0 (Python)"),
        (True, None, "mcp-panther/development (Python; Docker)"),
        (False, None, "mcp-panther/development (Python)"),
    ],
)
def test_get_user_agent(docker_running, version, expected):
    """Test user agent string generation with various conditions."""
    # Mock version function
    with (
        mock.patch("mcp_panther.panther_mcp_core.client.version", return_value=version)
        if version
        else mock.patch(
            "mcp_panther.panther_mcp_core.client.version",
            side_effect=Exception("Version not found"),
        )
    ):
        # Mock Docker detection
        with mock.patch(
            "mcp_panther.panther_mcp_core.client._is_running_in_docker",
            return_value=docker_running,
        ):
            assert _get_user_agent() == expected


@pytest.mark.asyncio
async def test_get_json_from_script_tag_success():
    """Test successful JSON extraction from script tag."""
    mock_response = mock.Mock(spec=ClientResponse)
    mock_response.status = 200
    mock_response.text.return_value = (
        '<script id="__PANTHER_CONFIG__">{"key": "value"}</script>'
    )

    with mock.patch("aiohttp.ClientSession.get") as mock_get:
        mock_get.return_value.__aenter__.return_value = mock_response
        result = await get_json_from_script_tag(
            "http://example.com", "__PANTHER_CONFIG__"
        )
        assert result == {"key": "value"}


@pytest.mark.asyncio
async def test_get_json_from_script_tag_error():
    """Test error handling when script tag is not found."""
    mock_response = mock.Mock(spec=ClientResponse)
    mock_response.status = 200
    mock_response.text.return_value = "<html><body>No config here</body></html>"

    with mock.patch("aiohttp.ClientSession.get") as mock_get:
        mock_get.return_value.__aenter__.return_value = mock_response
        with pytest.raises(ValueError) as exc_info:
            await get_json_from_script_tag("http://example.com", "__PANTHER_CONFIG__")
        assert "could not find json info" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_json_from_script_tag_unexpected_status():
    """Test handling of unexpected HTTP status codes."""
    mock_response = mock.Mock(spec=ClientResponse)
    mock_response.status = 404

    with mock.patch("aiohttp.ClientSession.get") as mock_get:
        mock_get.return_value.__aenter__.return_value = mock_response
        with pytest.raises(UnexpectedResponseStatusError) as exc_info:
            await get_json_from_script_tag("http://example.com", "__PANTHER_CONFIG__")
        assert "unexpected status code" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_instance_config_fallback():
    """Test fallback logic when config script tag returns error."""
    # Test with graphql URL
    with mock.patch(
        "mcp_panther.panther_mcp_core.client.get_panther_instance_url",
        return_value="http://example.com/public/graphql",
    ):
        with mock.patch(
            "mcp_panther.panther_mcp_core.client.get_json_from_script_tag",
            side_effect=UnexpectedResponseStatusError("test"),
        ):
            config = await get_instance_config()
            assert config == {"rest": "http://example.com"}

    # Test with regular URL
    with mock.patch(
        "mcp_panther.panther_mcp_core.client.get_panther_instance_url",
        return_value="http://example.com/",
    ):
        with mock.patch(
            "mcp_panther.panther_mcp_core.client.get_json_from_script_tag",
            side_effect=UnexpectedResponseStatusError("test"),
        ):
            config = await get_instance_config()
            assert config == {"rest": "http://example.com"}


@pytest.mark.asyncio
async def test_get_panther_rest_api_base():
    """Test REST API base URL resolution."""
    # Test direct REST URL
    with mock.patch(
        "mcp_panther.panther_mcp_core.client.get_instance_config",
        return_value={"rest": "http://example.com"},
    ):
        base = await get_panther_rest_api_base()
        assert base == "http://example.com"

    # Test graphql endpoint conversion
    with mock.patch(
        "mcp_panther.panther_mcp_core.client.get_instance_config",
        return_value={
            "WEB_APPLICATION_GRAPHQL_API_ENDPOINT": "http://example.com/internal/graphql"
        },
    ):
        base = await get_panther_rest_api_base()
        assert base == "http://example.com"

    # Test empty config
    with mock.patch(
        "mcp_panther.panther_mcp_core.client.get_instance_config", return_value=None
    ):
        base = await get_panther_rest_api_base()
        assert base == ""
