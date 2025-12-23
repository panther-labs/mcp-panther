"""Pytest configuration and fixtures for MCP Panther tests."""

import os

import pytest


def has_panther_credentials() -> bool:
    """Check if Panther API credentials are available in environment.

    Returns:
        True if both PANTHER_INSTANCE_URL and PANTHER_API_TOKEN environment
        variables are set and non-empty.
    """
    return bool(
        os.environ.get("PANTHER_INSTANCE_URL") and os.environ.get("PANTHER_API_TOKEN")
    )


# Marker for tests that require real Panther API credentials
needs_credentials = pytest.mark.skipif(
    not has_panther_credentials(),
    reason="Test requires PANTHER_INSTANCE_URL and PANTHER_API_TOKEN environment variables",
)
