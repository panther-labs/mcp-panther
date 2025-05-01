import pytest
from unittest.mock import patch
from click.testing import CliRunner

# Import your CLI entrypoint
from mcp_panther.server import main


@pytest.fixture
def mock_mcp_run():
    with patch("mcp_panther.server.mcp.run") as mock:
        yield mock


@pytest.fixture
def mock_asyncio_run():
    with patch("mcp_panther.server.asyncio.run") as mock:
        yield mock


def test_main_stdio_mode(mock_mcp_run, mock_asyncio_run):
    runner = CliRunner()
    result = runner.invoke(main, ["--transport", "stdio"])

    assert result.exit_code == 0
    assert mock_asyncio_run.called
