from unittest.mock import AsyncMock, patch

import pytest

from mcp_panther.panther_mcp_core.tools.saved_queries import (
    create_saved_query,
    get_saved_query,
    list_query_history,
    list_saved_queries,
)

SAVED_QUERIES_MODULE_PATH = "mcp_panther.panther_mcp_core.tools.saved_queries"

MOCK_QUERY_DATA = {
    "id": "query-123",
    "name": "Test Query",
    "description": "A test saved query",
    "sql": "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_occurs_since('1 d') AND errorcode IS NOT NULL",
    "enabled": False,
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

MOCK_EXECUTION_DATA = {
    "id": "01be9d03-0206-4f0f-000d-9eff006f748a",
    "sql": "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_occurs_since('1 d')",
    "status": "succeeded",
    "startedAt": "2025-08-25T20:51:40.104283996Z",
    "completedAt": "2025-08-25T20:51:41.298Z",
    "message": "The data lake query has successfully completed",
    "name": "Test Query",
    "isScheduled": True,
    "issuedBy": {"id": "test-user-123", "email": "test-user@example.com"},
    "bytesScanned": 473600.0,
    "executionTime": 1333.0,
    "rowCount": 0.0,
}

MOCK_EXECUTION_RESPONSE = {
    "dataLakeQueries": {
        "edges": [
            {
                "node": {
                    "id": "01be9d03-0206-4f0f-000d-9eff006f748a",
                    "sql": "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_occurs_since('1 d')",
                    "status": "succeeded",
                    "startedAt": "2025-08-25T20:51:40.104283996Z",
                    "completedAt": "2025-08-25T20:51:41.298Z",
                    "message": "The data lake query has successfully completed",
                    "name": "Test Query",
                    "isScheduled": True,
                    "issuedBy": {
                        "id": "test-user-123",
                        "email": "test-user@example.com",
                    },
                    "results": {
                        "stats": {
                            "bytesScanned": 473600.0,
                            "executionTime": 1333.0,
                            "rowCount": 0.0,
                        }
                    },
                }
            }
        ],
        "pageInfo": {"hasNextPage": False, "endCursor": None},
    }
}


def create_mock_rest_client():
    """Create a mock REST client for testing."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


def create_mock_graphql_client():
    """Create a mock GraphQL client for testing."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


@pytest.mark.asyncio
@patch(f"{SAVED_QUERIES_MODULE_PATH}.get_rest_client")
async def test_create_saved_query_success(mock_get_client):
    """Test successful creation of a saved query."""
    mock_client = create_mock_rest_client()
    mock_client.post.return_value = (MOCK_QUERY_DATA, 201)
    mock_get_client.return_value = mock_client

    result = await create_saved_query(
        name="Test Query",
        sql="SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_occurs_since('1 d') AND errorcode IS NOT NULL",
        description="A test saved query",
    )

    assert result["success"] is True
    assert result["query_id"] == "query-123"
    assert result["query"]["name"] == "Test Query"
    assert "Successfully created saved query 'Test Query'" in result["message"]

    mock_client.post.assert_called_once_with(
        "/queries",
        json={
            "name": "Test Query",
            "sql": "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_occurs_since('1 d') AND errorcode IS NOT NULL",
            "enabled": False,
            "description": "A test saved query",
        },
    )


@pytest.mark.asyncio
@patch(f"{SAVED_QUERIES_MODULE_PATH}.get_rest_client")
async def test_create_saved_query_with_schedule(mock_get_client):
    """Test successful creation of a scheduled query."""
    mock_client = create_mock_rest_client()
    mock_scheduled_query_data = dict(MOCK_QUERY_DATA)
    mock_scheduled_query_data["enabled"] = True
    mock_client.post.return_value = (mock_scheduled_query_data, 201)
    mock_get_client.return_value = mock_client

    result = await create_saved_query(
        name="Scheduled Test Query",
        sql="SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_occurs_since('1 d') AND errorcode IS NOT NULL",
        description="A test scheduled query",
        enabled=True,
        cron_expression="0 9 * * 1",
        timeout_minutes=45,
    )

    assert result["success"] is True
    assert result["query_id"] == "query-123"
    assert (
        "Successfully created saved query 'Scheduled Test Query'" in result["message"]
    )

    mock_client.post.assert_called_once_with(
        "/queries",
        json={
            "name": "Scheduled Test Query",
            "sql": "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_occurs_since('1 d') AND errorcode IS NOT NULL",
            "enabled": True,
            "description": "A test scheduled query",
            "schedule": {
                "cron": "0 9 * * 1",
                "disabled": False,
                "timeoutMinutes": 45,
            },
        },
    )


@pytest.mark.asyncio
@patch(f"{SAVED_QUERIES_MODULE_PATH}.get_rest_client")
async def test_create_saved_query_without_description(mock_get_client):
    """Test creation of saved query without description."""
    mock_client = create_mock_rest_client()
    mock_client.post.return_value = (MOCK_QUERY_DATA, 201)
    mock_get_client.return_value = mock_client

    result = await create_saved_query(
        name="Test Query",
        sql="SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_occurs_since('1 d')",
    )

    assert result["success"] is True

    mock_client.post.assert_called_once_with(
        "/queries",
        json={
            "name": "Test Query",
            "sql": "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_occurs_since('1 d')",
            "enabled": False,
        },
    )


@pytest.mark.asyncio
async def test_create_saved_query_validation_errors():
    """Test validation errors for create_saved_query."""
    # Note: BeforeValidator errors are caught at the tool invocation level,
    # so we expect general error messages here

    # Test empty name - this will be caught by BeforeValidator
    result = await create_saved_query(
        name="", sql="SELECT 1 WHERE p_occurs_since('1 d')"
    )
    assert result["success"] is False
    # BeforeValidator error gets wrapped in a generic error message

    # Test empty SQL - this will be caught by BeforeValidator
    result = await create_saved_query(name="Test", sql="")
    assert result["success"] is False

    # Test missing p_event_time filter - this will be caught by BeforeValidator
    result = await create_saved_query(name="Test", sql="SELECT 1")
    assert result["success"] is False

    # Test enabled=True without cron_expression - this is checked in the function
    result = await create_saved_query(
        name="Test", sql="SELECT * FROM table WHERE p_occurs_since('1 d')", enabled=True
    )
    assert result["success"] is False
    assert "cron_expression is required when enabled=True" in result["message"]


@pytest.mark.asyncio
@patch(f"{SAVED_QUERIES_MODULE_PATH}.get_rest_client")
async def test_create_saved_query_error(mock_get_client):
    """Test handling of errors when creating saved query."""
    mock_client = create_mock_rest_client()
    mock_client.post.side_effect = Exception("API Error")
    mock_get_client.return_value = mock_client

    result = await create_saved_query(
        name="Test Query",
        sql="SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_occurs_since('1 d')",
    )

    assert result["success"] is False
    assert "Failed to create saved query" in result["message"]
    assert "API Error" in result["message"]


@pytest.mark.asyncio
@patch(f"{SAVED_QUERIES_MODULE_PATH}.get_rest_client")
async def test_list_saved_queries_success(mock_get_client):
    """Test successful listing of saved queries."""
    mock_client = create_mock_rest_client()
    mock_client.get.return_value = (MOCK_QUERY_LIST, 200)
    mock_get_client.return_value = mock_client

    result = await list_saved_queries()

    assert result["success"] is True
    assert len(result["queries"]) == 1
    assert result["queries"][0]["id"] == "query-123"
    assert result["total_queries"] == 1
    assert result["has_next_page"] is False
    assert result["next_cursor"] is None

    mock_client.get.assert_called_once_with("/queries", params={"limit": 100})


@pytest.mark.asyncio
@patch(f"{SAVED_QUERIES_MODULE_PATH}.get_rest_client")
async def test_list_saved_queries_with_pagination(mock_get_client):
    """Test listing saved queries with pagination parameters."""
    mock_client = create_mock_rest_client()
    mock_query_list_with_next = {
        "results": [MOCK_QUERY_DATA],
        "next": "next-cursor-token",
    }
    mock_client.get.return_value = (mock_query_list_with_next, 200)
    mock_get_client.return_value = mock_client

    result = await list_saved_queries(cursor="test-cursor", limit=50)

    assert result["success"] is True
    assert result["has_next_page"] is True
    assert result["next_cursor"] == "next-cursor-token"

    mock_client.get.assert_called_once_with(
        "/queries", params={"limit": 50, "cursor": "test-cursor"}
    )


@pytest.mark.asyncio
@patch(f"{SAVED_QUERIES_MODULE_PATH}.get_rest_client")
async def test_list_saved_queries_error(mock_get_client):
    """Test handling of errors when listing saved queries."""
    mock_client = create_mock_rest_client()
    mock_client.get.side_effect = Exception("API Error")
    mock_get_client.return_value = mock_client

    result = await list_saved_queries()

    assert result["success"] is False
    assert "Failed to list saved queries" in result["message"]
    assert "API Error" in result["message"]


@pytest.mark.asyncio
@patch(f"{SAVED_QUERIES_MODULE_PATH}.get_rest_client")
async def test_list_saved_queries_name_contains_and_sql_removal(mock_get_client):
    """Test filtering saved queries by name_contains and removal of 'sql' field."""
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
    result = await list_saved_queries(name_contains="test")
    assert result["success"] is True
    assert result["total_queries"] == 1
    assert result["queries"][0]["id"] == "query-123"
    assert "sql" not in result["queries"][0]

    # Should only return queries whose name contains 'another' (case-insensitive)
    result2 = await list_saved_queries(name_contains="another")
    assert result2["success"] is True
    assert result2["total_queries"] == 1
    assert result2["queries"][0]["id"] == "query-456"
    assert "sql" not in result2["queries"][0]

    # Should return both queries if no filter is applied
    result3 = await list_saved_queries()
    assert result3["success"] is True
    assert result3["total_queries"] == 2
    for q in result3["queries"]:
        assert "sql" not in q


@pytest.mark.asyncio
@patch(f"{SAVED_QUERIES_MODULE_PATH}.get_rest_client")
async def test_get_saved_query_success(mock_get_client):
    """Test successful retrieval of a specific saved query."""
    mock_client = create_mock_rest_client()
    mock_client.get.return_value = (MOCK_QUERY_DATA, 200)
    mock_get_client.return_value = mock_client

    result = await get_saved_query("query-123")

    assert result["success"] is True
    assert result["query"]["id"] == "query-123"
    assert result["query"]["name"] == "Test Query"
    assert result["query"]["schedule"]["cron"] == "0 9 * * 1"

    mock_client.get.assert_called_once_with("/queries/query-123")


@pytest.mark.asyncio
@patch(f"{SAVED_QUERIES_MODULE_PATH}.get_rest_client")
async def test_get_saved_query_error(mock_get_client):
    """Test handling of errors when getting a saved query."""
    mock_client = create_mock_rest_client()
    mock_client.get.side_effect = Exception("Not Found")
    mock_get_client.return_value = mock_client

    result = await get_saved_query("nonexistent-query")

    assert result["success"] is False
    assert "Failed to fetch saved query" in result["message"]
    assert "Not Found" in result["message"]


@pytest.mark.asyncio
@patch(f"{SAVED_QUERIES_MODULE_PATH}._create_panther_client")
async def test_list_query_history_success(mock_create_client):
    """Test successful listing of query execution history."""
    mock_client = AsyncMock()
    mock_client.execute_async.return_value = MOCK_EXECUTION_RESPONSE
    mock_create_client.return_value = mock_client

    result = await list_query_history()

    assert result["success"] is True
    assert len(result["executions"]) == 1
    assert result["executions"][0]["id"] == "01be9d03-0206-4f0f-000d-9eff006f748a"
    assert result["executions"][0]["status"] == "succeeded"
    assert result["executions"][0]["bytesScanned"] == 473600.0
    assert result["executions"][0]["executionTime"] == 1333.0
    assert result["executions"][0]["rowCount"] == 0.0
    assert result["total_executions"] == 1
    assert result["has_next_page"] is False
    assert result["next_cursor"] is None

    mock_client.execute_async.assert_called_once()
    # Verify the variables passed
    call_args = mock_client.execute_async.call_args
    assert call_args[1]["variable_values"] == {"input": {"pageSize": 25}}


@pytest.mark.asyncio
@patch(f"{SAVED_QUERIES_MODULE_PATH}._create_panther_client")
async def test_list_query_history_with_pagination(mock_create_client):
    """Test listing query history with pagination."""
    mock_client = AsyncMock()
    mock_execution_response_with_next = {
        "dataLakeQueries": {
            "edges": [
                {
                    "node": {
                        "id": "01be9d03-0206-4f0f-000d-9eff006f748a",
                        "sql": "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_occurs_since('1 d')",
                        "status": "succeeded",
                        "startedAt": "2025-08-25T20:51:40.104283996Z",
                        "completedAt": "2025-08-25T20:51:41.298Z",
                        "message": "The data lake query has successfully completed",
                        "name": "Test Query",
                        "isScheduled": True,
                        "issuedBy": {
                            "id": "test-user-123",
                            "email": "test-user@example.com",
                        },
                        "results": {
                            "stats": {
                                "bytesScanned": 473600.0,
                                "executionTime": 1333.0,
                                "rowCount": 0.0,
                            }
                        },
                    }
                }
            ],
            "pageInfo": {"hasNextPage": True, "endCursor": "next-cursor-token"},
        }
    }
    mock_client.execute_async.return_value = mock_execution_response_with_next
    mock_create_client.return_value = mock_client

    result = await list_query_history(cursor="test-cursor", limit=10)

    assert result["success"] is True
    assert result["has_next_page"] is True
    assert result["next_cursor"] == "next-cursor-token"

    # Verify the GraphQL query variables
    call_args = mock_client.execute_async.call_args
    assert call_args[1]["variable_values"] == {
        "input": {"pageSize": 10, "cursor": "test-cursor"}
    }


@pytest.mark.asyncio
@patch(f"{SAVED_QUERIES_MODULE_PATH}._create_panther_client")
async def test_list_query_history_failed_execution(mock_create_client):
    """Test listing query history with failed execution."""
    mock_client = AsyncMock()
    mock_failed_execution_response = {
        "dataLakeQueries": {
            "edges": [
                {
                    "node": {
                        "id": "01be9bfe-0206-4d7c-000d-9eff006c9a76",
                        "sql": "SELECT invalid_column FROM invalid_table",
                        "status": "failed",
                        "startedAt": "2025-08-25T16:30:53.33041179Z",
                        "completedAt": "2025-08-25T16:30:55.06007564Z",
                        "message": "SQL compilation error: invalid identifier 'INVALID_COLUMN'",
                        "name": None,
                        "isScheduled": False,
                        "issuedBy": {"id": "po_mcvoepetd3", "name": "JN-MCP"},
                        "results": None,
                    }
                }
            ],
            "pageInfo": {"hasNextPage": False, "endCursor": None},
        }
    }
    mock_client.execute_async.return_value = mock_failed_execution_response
    mock_create_client.return_value = mock_client

    result = await list_query_history()

    assert result["success"] is True
    assert len(result["executions"]) == 1
    assert result["executions"][0]["status"] == "failed"
    assert "SQL compilation error" in result["executions"][0]["message"]
    assert result["executions"][0]["bytesScanned"] is None
    assert result["executions"][0]["executionTime"] is None
    assert result["executions"][0]["rowCount"] is None


@pytest.mark.asyncio
@patch(f"{SAVED_QUERIES_MODULE_PATH}._create_panther_client")
async def test_list_query_history_exception(mock_create_client):
    """Test handling of exceptions when listing query history."""
    mock_create_client.side_effect = Exception("GraphQL connection failed")

    result = await list_query_history()

    assert result["success"] is False
    assert "Failed to list query history" in result["message"]
    assert "GraphQL connection failed" in result["message"]


@pytest.mark.asyncio
@patch(f"{SAVED_QUERIES_MODULE_PATH}._create_panther_client")
async def test_list_query_history_empty_results(mock_create_client):
    """Test listing query history with no results."""
    mock_client = AsyncMock()
    mock_empty_response = {
        "dataLakeQueries": {
            "edges": [],
            "pageInfo": {"hasNextPage": False, "endCursor": None},
        }
    }
    mock_client.execute_async.return_value = mock_empty_response
    mock_create_client.return_value = mock_client

    result = await list_query_history()

    assert result["success"] is True
    assert len(result["executions"]) == 0
    assert result["total_executions"] == 0
    assert result["has_next_page"] is False
    assert result["next_cursor"] is None
