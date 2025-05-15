import os
from unittest import mock

import pytest

from mcp_panther.panther_mcp_core.client import _is_running_in_docker, _get_user_agent


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
    with mock.patch.dict(os.environ, {"MCP_PANTHER_DOCKER_RUNTIME": env_value} if env_value is not None else {}):
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
    with mock.patch("mcp_panther.panther_mcp_core.client.version", return_value=version) if version else mock.patch(
        "mcp_panther.panther_mcp_core.client.version", side_effect=Exception("Version not found")
    ):
        # Mock Docker detection
        with mock.patch("mcp_panther.panther_mcp_core.client._is_running_in_docker", return_value=docker_running):
            assert _get_user_agent() == expected 
