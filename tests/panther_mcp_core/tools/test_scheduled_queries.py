from unittest.mock import AsyncMock, patch

import pytest

from mcp_panther.panther_mcp_core.tools.scheduled_queries import (
    get_scheduled_query,
    list_scheduled_queries,
)

SCHEDULED_QUERIES_MODULE_PATH = "mcp_panther.panther_mcp_core.tools.scheduled_queries"

MOCK_QUERY_DATA = {
    "id": "query-123",
    "name": "Test Query",
    "description": "A test scheduled query",
    "sql": "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_event_time >= DATEADD(day, -1, CURRENT_TIMESTAMP())",
    "schedule": {
        "cron": "0 9 * * 1",
        "disabled": False,
        "rateMinutes": None,
        "timeoutMinutes": 30,
    },
    "managed": False,
    "createdAt": "2024-01-01T09:00:00Z",
    "updatedAt": "2024-01-01T09:00:00Z",
}

MOCK_QUERY_LIST = {
    "results": [MOCK_QUERY_DATA],
    "next": None,
}


def create_mock_rest_client():
    """Create a mock REST client for testing."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


@pytest.mark.asyncio
@patch(f"{SCHEDULED_QUERIES_MODULE_PATH}.get_rest_client")
async def test_list_scheduled_queries_success(mock_get_client):
    """Test successful listing of scheduled queries."""
    mock_client = create_mock_rest_client()
    mock_client.get.return_value = (MOCK_QUERY_LIST, 200)
    mock_get_client.return_value = mock_client

    result = await list_scheduled_queries()

    assert result["success"] is True
    assert len(result["queries"]) == 1
    assert result["queries"][0]["id"] == "query-123"
    assert result["total_queries"] == 1
    assert result["has_next_page"] is False
    assert result["next_cursor"] is None

    mock_client.get.assert_called_once_with("/queries", params={"limit": 100})


@pytest.mark.asyncio
@patch(f"{SCHEDULED_QUERIES_MODULE_PATH}.get_rest_client")
async def test_list_scheduled_queries_with_pagination(mock_get_client):
    """Test listing scheduled queries with pagination parameters."""
    mock_client = create_mock_rest_client()
    mock_query_list_with_next = {
        "results": [MOCK_QUERY_DATA],
        "next": "next-cursor-token",
    }
    mock_client.get.return_value = (mock_query_list_with_next, 200)
    mock_get_client.return_value = mock_client

    result = await list_scheduled_queries(cursor="test-cursor", limit=50)

    assert result["success"] is True
    assert result["has_next_page"] is True
    assert result["next_cursor"] == "next-cursor-token"

    mock_client.get.assert_called_once_with(
        "/queries", params={"limit": 50, "cursor": "test-cursor"}
    )


@pytest.mark.asyncio
@patch(f"{SCHEDULED_QUERIES_MODULE_PATH}.get_rest_client")
async def test_list_scheduled_queries_error(mock_get_client):
    """Test handling of errors when listing scheduled queries."""
    mock_client = create_mock_rest_client()
    mock_client.get.side_effect = Exception("API Error")
    mock_get_client.return_value = mock_client

    result = await list_scheduled_queries()

    assert result["success"] is False
    assert "Failed to list scheduled queries" in result["message"]
    assert "API Error" in result["message"]


@pytest.mark.asyncio
@patch(f"{SCHEDULED_QUERIES_MODULE_PATH}.get_rest_client")
async def test_list_scheduled_queries_name_contains_and_sql_removal(mock_get_client):
    """Test filtering scheduled queries by name_contains and removal of 'sql' field."""
    mock_client = create_mock_rest_client()
    # Add a second query to test filtering
    query1 = dict(MOCK_QUERY_DATA)
    query2 = dict(MOCK_QUERY_DATA)
    query2["id"] = "query-456"
    query2["name"] = "Another Query"
    query2["sql"] = "SELECT 1"
    mock_query_list = {
        "results": [query1, query2],
        "next": None,
    }
    mock_client.get.return_value = (mock_query_list, 200)
    mock_get_client.return_value = mock_client

    # Should only return queries whose name contains 'test' (case-insensitive)
    result = await list_scheduled_queries(name_contains="test")
    assert result["success"] is True
    assert result["total_queries"] == 1
    assert result["queries"][0]["id"] == "query-123"
    assert "sql" not in result["queries"][0]

    # Should only return queries whose name contains 'another' (case-insensitive)
    result2 = await list_scheduled_queries(name_contains="another")
    assert result2["success"] is True
    assert result2["total_queries"] == 1
    assert result2["queries"][0]["id"] == "query-456"
    assert "sql" not in result2["queries"][0]

    # Should return both queries if no filter is applied
    result3 = await list_scheduled_queries()
    assert result3["success"] is True
    assert result3["total_queries"] == 2
    for q in result3["queries"]:
        assert "sql" not in q


@pytest.mark.asyncio
@patch(f"{SCHEDULED_QUERIES_MODULE_PATH}.get_rest_client")
async def test_get_scheduled_query_success(mock_get_client):
    """Test successful retrieval of a specific scheduled query."""
    mock_client = create_mock_rest_client()
    mock_client.get.return_value = (MOCK_QUERY_DATA, 200)
    mock_get_client.return_value = mock_client

    result = await get_scheduled_query("query-123")

    assert result["success"] is True
    assert result["query"]["id"] == "query-123"
    assert result["query"]["name"] == "Test Query"
    assert result["query"]["schedule"]["cron"] == "0 9 * * 1"

    mock_client.get.assert_called_once_with("/queries/query-123")


@pytest.mark.asyncio
@patch(f"{SCHEDULED_QUERIES_MODULE_PATH}.get_rest_client")
async def test_get_scheduled_query_error(mock_get_client):
    """Test handling of errors when getting a scheduled query."""
    mock_client = create_mock_rest_client()
    mock_client.get.side_effect = Exception("Not Found")
    mock_get_client.return_value = mock_client

    result = await get_scheduled_query("nonexistent-query")

    assert result["success"] is False
    assert "Failed to fetch scheduled query" in result["message"]
    assert "Not Found" in result["message"]
