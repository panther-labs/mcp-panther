from click.testing import CliRunner
from unittest.mock import patch
from mcp_panther.server import main  # Adjust import to your module layout


def test_main_runs_mcp_stdio():
    runner = CliRunner()

    with patch("mcp_panther.server.mcp.run") as mock_run:
        result = runner.invoke(main, ["--transport", "stdio"])

    assert result.exit_code == 0
    mock_run.assert_called_once_with(transport="stdio")
