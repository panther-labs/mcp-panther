from unittest.mock import patch

import pytest

from mcp_panther.panther_mcp_core.tools.data_lake import (
    _cancel_data_lake_query,
    execute_data_lake_query,
    wrap_reserved_words,
)
from tests.utils.helpers import patch_graphql_client

DATA_LAKE_MODULE_PATH = "mcp_panther.panther_mcp_core.tools.data_lake"

MOCK_QUERY_ID = "query-123456789"


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_execute_data_lake_query_success(mock_graphql_client):
    """Test successful execution of a data lake query."""
    mock_graphql_client.execute.return_value = {
        "executeDataLakeQuery": {"id": MOCK_QUERY_ID}
    }
    sql = "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_event_time >= DATEADD(day, -30, CURRENT_TIMESTAMP()) LIMIT 10"
    with patch(f"{DATA_LAKE_MODULE_PATH}._get_data_lake_query_results") as mock_res:
        mock_res.return_value = {
            "success": True,
            "status": "succeeded",
            "results": [],
            "column_info": {},
            "stats": {},
            "has_next_page": False,
            "end_cursor": None,
            "message": "Query executed successfully",
        }
        result = await execute_data_lake_query(sql)

    assert result["success"] is True
    assert result["status"] == "succeeded"

    mock_graphql_client.execute.assert_called_once()
    call_args = mock_graphql_client.execute.call_args[1]["variable_values"]
    assert call_args["input"]["sql"] == sql
    assert call_args["input"]["databaseName"] == "panther_logs.public"


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_execute_data_lake_query_custom_database(mock_graphql_client):
    """Test executing a data lake query with a custom database."""
    mock_graphql_client.execute.return_value = {
        "executeDataLakeQuery": {"id": MOCK_QUERY_ID}
    }
    sql = "SELECT * FROM my_custom_table WHERE p_event_time >= DATEADD(day, -30, CURRENT_TIMESTAMP()) LIMIT 10"
    custom_db = "custom_database"
    with patch(f"{DATA_LAKE_MODULE_PATH}._get_data_lake_query_results") as mock_res:
        mock_res.return_value = {
            "success": True,
            "status": "succeeded",
            "results": [],
            "column_info": {},
            "stats": {},
            "has_next_page": False,
            "end_cursor": None,
            "message": "Query executed successfully",
        }
        result = await execute_data_lake_query(sql, database_name=custom_db)

    assert result["success"] is True
    assert result["status"] == "succeeded"

    call_args = mock_graphql_client.execute.call_args[1]["variable_values"]
    assert call_args["input"]["databaseName"] == custom_db


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_execute_data_lake_query_error(mock_graphql_client):
    """Test handling of errors when executing a data lake query."""
    mock_graphql_client.execute.side_effect = Exception("Test error")

    sql = "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_event_time >= DATEADD(day, -30, CURRENT_TIMESTAMP()) LIMIT 10"
    result = await execute_data_lake_query(sql)

    assert result["success"] is False
    assert "Failed to execute data lake query" in result["message"]


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_execute_data_lake_query_missing_event_time(mock_graphql_client):
    """Test that queries without p_event_time filter are rejected."""
    sql = "SELECT * FROM panther_logs.public.aws_cloudtrail LIMIT 10"
    result = await execute_data_lake_query(sql)

    assert result["success"] is False
    assert (
        "Query must include `p_event_time` as a filter condition after WHERE or AND"
        in result["message"]
    )
    mock_graphql_client.execute.assert_not_called()


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_execute_data_lake_query_with_event_time(mock_graphql_client):
    """Test that queries with p_event_time filter are accepted."""
    mock_graphql_client.execute.return_value = {
        "executeDataLakeQuery": {"id": MOCK_QUERY_ID}
    }

    # Test various valid filter patterns
    valid_queries = [
        "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_event_time >= DATEADD(day, -30, CURRENT_TIMESTAMP()) LIMIT 10",
        "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE (p_event_time >= DATEADD(day, -30, CURRENT_TIMESTAMP()) AND other_condition) LIMIT 10",
        "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE other_condition AND p_event_time >= DATEADD(day, -30, CURRENT_TIMESTAMP()) LIMIT 10",
        # Test table-qualified p_event_time fields
        "SELECT * FROM panther_logs.public.aws_cloudtrail t WHERE t.p_event_time >= DATEADD(day, -30, CURRENT_TIMESTAMP()) LIMIT 10",
        "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE aws_cloudtrail.p_event_time >= DATEADD(day, -30, CURRENT_TIMESTAMP()) LIMIT 10",
        "SELECT * FROM panther_logs.public.aws_cloudtrail t1 WHERE t1.p_event_time >= DATEADD(day, -30, CURRENT_TIMESTAMP()) LIMIT 10",
        "SELECT * FROM panther_logs.public.aws_cloudtrail t1 WHERE other_condition AND t1.p_event_time >= DATEADD(day, -30, CURRENT_TIMESTAMP()) LIMIT 10",
    ]

    with patch(f"{DATA_LAKE_MODULE_PATH}._get_data_lake_query_results") as mock_res:
        mock_res.return_value = {
            "success": True,
            "status": "succeeded",
            "results": [],
            "column_info": {},
            "stats": {},
            "has_next_page": False,
            "end_cursor": None,
            "message": "Query executed successfully",
        }
        for sql in valid_queries:
            result = await execute_data_lake_query(sql)
            assert result["success"] is True, f"Query failed: {sql}"
            assert result["status"] == "succeeded"
            mock_graphql_client.execute.assert_called_once()
            mock_graphql_client.execute.reset_mock()


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_execute_data_lake_query_invalid_event_time_usage(mock_graphql_client):
    """Test that queries with invalid p_event_time usage are rejected."""
    mock_graphql_client.execute.return_value = {
        "executeDataLakeQuery": {"id": MOCK_QUERY_ID}
    }

    invalid_queries = [
        # p_event_time in SELECT
        "SELECT p_event_time FROM panther_logs.public.aws_cloudtrail LIMIT 10",
        # p_event_time as a value
        "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE other_column = p_event_time LIMIT 10",
        # p_event_time without WHERE/AND
        "SELECT * FROM panther_logs.public.aws_cloudtrail LIMIT 10",
        # p_event_time in a subquery
        "SELECT * FROM (SELECT p_event_time FROM panther_logs.public.aws_cloudtrail) LIMIT 10",
        # Invalid table-qualified p_event_time usage
        "SELECT t.p_event_time FROM panther_logs.public.aws_cloudtrail t LIMIT 10",
        "SELECT * FROM panther_logs.public.aws_cloudtrail t WHERE other_column = t.p_event_time LIMIT 10",
        "SELECT * FROM (SELECT t.p_event_time FROM panther_logs.public.aws_cloudtrail t) LIMIT 10",
    ]

    for sql in invalid_queries:
        result = await execute_data_lake_query(sql)
        assert result["success"] is False, f"Query should have failed: {sql}"
        assert (
            "Query must include `p_event_time` as a filter condition after WHERE or AND"
            in result["message"]
        )
        mock_graphql_client.execute.assert_not_called()


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_cancel_data_lake_query_success(mock_graphql_client):
    """Test successful cancellation of a data lake query."""
    mock_response = {"cancelDataLakeQuery": {"id": "query123"}}
    mock_graphql_client.execute.return_value = mock_response

    result = await _cancel_data_lake_query("query123")

    assert result["success"] is True
    assert result["query_id"] == "query123"
    assert "Successfully cancelled" in result["message"]

    # Verify correct GraphQL call
    call_args = mock_graphql_client.execute.call_args[1]["variable_values"]
    assert call_args["input"]["id"] == "query123"


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_cancel_data_lake_query_not_found(mock_graphql_client):
    """Test cancellation of a non-existent query."""
    mock_graphql_client.execute.side_effect = Exception("Query not found")

    result = await _cancel_data_lake_query("nonexistent")

    assert result["success"] is False
    assert "not found" in result["message"]
    assert "already completed or been cancelled" in result["message"]


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_cancel_data_lake_query_cannot_cancel(mock_graphql_client):
    """Test cancellation of a query that cannot be cancelled."""
    mock_graphql_client.execute.side_effect = Exception("Query cannot be cancelled")

    result = await _cancel_data_lake_query("completed_query")

    assert result["success"] is False
    assert "cannot be cancelled" in result["message"]
    assert "Only running queries" in result["message"]


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_cancel_data_lake_query_permission_error(mock_graphql_client):
    """Test cancellation with permission error."""
    mock_graphql_client.execute.side_effect = Exception("Permission denied")

    result = await _cancel_data_lake_query("query123")

    assert result["success"] is False
    assert "Permission denied" in result["message"]


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_cancel_data_lake_query_no_id_returned(mock_graphql_client):
    """Test cancellation when no ID is returned."""
    mock_response = {"cancelDataLakeQuery": {}}
    mock_graphql_client.execute.return_value = mock_response

    result = await _cancel_data_lake_query("query123")

    assert result["success"] is False
    assert "No query ID returned" in result["message"]


# Reserved Words Tests


def test_wrap_reserved_words_basic():
    """Test basic reserved word wrapping."""
    test_cases = [
        {
            "input": "SELECT eventName as 'select', awsRegion as 'from' FROM aws_cloudtrail",
            "expected": 'SELECT eventName as "select", awsRegion as "from" FROM aws_cloudtrail',
        },
        {
            "input": "SELECT 'table', 'column', 'index' FROM aws_cloudtrail",
            "expected": 'SELECT "table", "column", "index" FROM aws_cloudtrail',
        },
        {
            "input": "SELECT eventName FROM aws_cloudtrail WHERE 'where' > 100",
            "expected": 'SELECT eventName FROM aws_cloudtrail WHERE "where" > 100',
        },
    ]

    for case in test_cases:
        result = wrap_reserved_words(case["input"])
        assert result == case["expected"], (
            f"Expected '{case['expected']}' but got '{result}'"
        )


def test_wrap_reserved_words_preserves_non_reserved():
    """Test that non-reserved words are not modified."""
    sql = "SELECT eventName FROM aws_cloudtrail WHERE eventTime > '2024-01-01'"
    result = wrap_reserved_words(sql)

    # Should not quote non-reserved words
    assert '"2024-01-01"' not in result
    assert "'2024-01-01'" in result


def test_wrap_reserved_words_complex_query():
    """Test reserved words in complex queries."""
    sql = """
    SELECT eventName as 'select', awsRegion as 'from'
    FROM aws_cloudtrail 
    WHERE p_event_time >= CURRENT_TIMESTAMP() - INTERVAL '1 DAY'
    ORDER BY 'select', 'from'
    """

    expected = """
    SELECT eventName as "select", awsRegion as "from"
    FROM aws_cloudtrail 
    WHERE p_event_time >= CURRENT_TIMESTAMP() - INTERVAL '1 DAY'
    ORDER BY "select", "from"
    """

    result = wrap_reserved_words(sql)
    assert result == expected


def test_wrap_reserved_words_handles_errors():
    """Test that function handles malformed SQL gracefully."""
    malformed_sql = "SELECT FROM WHERE ((("
    result = wrap_reserved_words(malformed_sql)
    # Should return original SQL if parsing fails
    assert result == malformed_sql


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_execute_data_lake_query_with_reserved_words_processing(
    mock_graphql_client,
):
    """Test that execute_data_lake_query processes reserved words."""
    mock_graphql_client.execute.return_value = {
        "executeDataLakeQuery": {"id": MOCK_QUERY_ID}
    }

    # SQL with single-quoted reserved words that should be converted to double-quoted
    input_sql = "SELECT eventName as 'select', awsRegion as 'from' FROM panther_logs.public.aws_cloudtrail WHERE p_event_time >= DATEADD(day, -30, CURRENT_TIMESTAMP()) LIMIT 10"
    expected_processed_sql = 'SELECT eventName as "select", awsRegion as "from" FROM panther_logs.public.aws_cloudtrail WHERE p_event_time >= DATEADD(day, -30, CURRENT_TIMESTAMP()) LIMIT 10'

    # Mock the query results function to return success
    with patch(f"{DATA_LAKE_MODULE_PATH}._get_data_lake_query_results") as mock_results:
        mock_results.return_value = {
            "success": True,
            "status": "succeeded",
            "results": [],
            "column_info": {},
            "stats": {},
            "has_next_page": False,
            "end_cursor": None,
            "message": "Query executed successfully",
        }

        result = await execute_data_lake_query(input_sql)

    # Verify the function returns success
    assert result["success"] is True
    assert result["status"] == "succeeded"

    # Verify the SQL was processed for reserved words
    call_args = mock_graphql_client.execute.call_args[1]["variable_values"]
    processed_sql = call_args["input"]["sql"]

    # Assert the exact transformed SQL
    assert processed_sql == expected_processed_sql
