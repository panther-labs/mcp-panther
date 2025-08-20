from unittest.mock import patch

import pytest

from mcp_panther.panther_mcp_core.tools.data_lake import (
    _cancel_data_lake_query,
    query_data_lake,
    wrap_reserved_words,
)
from tests.utils.helpers import patch_graphql_client

DATA_LAKE_MODULE_PATH = "mcp_panther.panther_mcp_core.tools.data_lake"

MOCK_QUERY_ID = "query-123456789"


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_query_data_lake_success(mock_graphql_client):
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
            "next_cursor": None,
            "message": "Query executed successfully",
            "query_id": MOCK_QUERY_ID,
        }
        result = await query_data_lake(sql)

    assert result["success"] is True
    assert result["status"] == "succeeded"
    assert result["query_id"] == MOCK_QUERY_ID

    mock_graphql_client.execute.assert_called_once()
    call_args = mock_graphql_client.execute.call_args[1]["variable_values"]
    assert call_args["input"]["sql"] == sql
    assert call_args["input"]["databaseName"] == "panther_logs.public"


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_query_data_lake_custom_database(mock_graphql_client):
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
            "next_cursor": None,
            "message": "Query executed successfully",
            "query_id": MOCK_QUERY_ID,
        }
        result = await query_data_lake(sql, database_name=custom_db)

    assert result["success"] is True
    assert result["status"] == "succeeded"
    assert result["query_id"] == MOCK_QUERY_ID

    call_args = mock_graphql_client.execute.call_args[1]["variable_values"]
    assert call_args["input"]["databaseName"] == custom_db


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_query_data_lake_error(mock_graphql_client):
    """Test handling of errors when executing a data lake query."""
    mock_graphql_client.execute.side_effect = Exception("Test error")

    sql = "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_event_time >= DATEADD(day, -30, CURRENT_TIMESTAMP()) LIMIT 10"
    result = await query_data_lake(sql)

    assert result["success"] is False
    assert "Failed to execute data lake query" in result["message"]
    assert (
        result["query_id"] is None
    )  # No query_id when error occurs before query execution


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_query_data_lake_missing_event_time(mock_graphql_client):
    """Test that queries without p_event_time filter are rejected."""
    sql = "SELECT * FROM panther_logs.public.aws_cloudtrail LIMIT 10"
    result = await query_data_lake(sql)

    assert result["success"] is False
    assert (
        "Query must include a time filter: either `p_event_time` condition or Panther macro"
        in result["message"]
    )
    assert result["query_id"] is None  # No query_id when validation fails
    mock_graphql_client.execute.assert_not_called()


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_query_data_lake_with_event_time(mock_graphql_client):
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
        # Test Panther time macros
        "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_occurs_since('1 d') LIMIT 10",
        "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_occurs_between('2024-01-01', '2024-01-02') LIMIT 10",
        "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_occurs_around('2024-01-01 10:00:00', '10 m') LIMIT 10",
        "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_occurs_after('2024-01-01') AND other_condition LIMIT 10",
        "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE other_condition AND p_occurs_before('2024-01-01') LIMIT 10",
    ]

    with patch(f"{DATA_LAKE_MODULE_PATH}._get_data_lake_query_results") as mock_res:
        mock_res.return_value = {
            "success": True,
            "status": "succeeded",
            "results": [],
            "column_info": {},
            "stats": {},
            "has_next_page": False,
            "next_cursor": None,
            "message": "Query executed successfully",
            "query_id": MOCK_QUERY_ID,
        }
        for sql in valid_queries:
            result = await query_data_lake(sql)
            assert result["success"] is True, f"Query failed: {sql}"
            assert result["status"] == "succeeded"
            assert result["query_id"] == MOCK_QUERY_ID
            mock_graphql_client.execute.assert_called_once()
            mock_graphql_client.execute.reset_mock()


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_query_data_lake_invalid_event_time_usage(mock_graphql_client):
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
        result = await query_data_lake(sql)
        assert result["success"] is False, f"Query should have failed: {sql}"
        assert (
            "Query must include a time filter: either `p_event_time` condition or Panther macro"
            in result["message"]
        )
        assert result["query_id"] is None  # No query_id when validation fails
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
async def test_query_data_lake_with_reserved_words_processing(
    mock_graphql_client,
):
    """Test that query_data_lake processes reserved words."""
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
            "next_cursor": None,
            "message": "Query executed successfully",
            "query_id": MOCK_QUERY_ID,
        }

        result = await query_data_lake(input_sql)

    # Verify the function returns success
    assert result["success"] is True
    assert result["status"] == "succeeded"
    assert result["query_id"] == MOCK_QUERY_ID

    # Verify the SQL was processed for reserved words
    call_args = mock_graphql_client.execute.call_args[1]["variable_values"]
    processed_sql = call_args["input"]["sql"]

    # Assert the exact transformed SQL
    assert processed_sql == expected_processed_sql


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_query_data_lake_with_cursor_pagination(
    mock_graphql_client,
):
    """Test that query_data_lake supports cursor-based pagination."""
    mock_graphql_client.execute.return_value = {
        "executeDataLakeQuery": {"id": MOCK_QUERY_ID}
    }

    cursor = "pagination_cursor_123"
    test_sql = (
        "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_occurs_since('1 d')"
    )

    # Mock the query results function to return paginated response
    with patch(f"{DATA_LAKE_MODULE_PATH}._get_data_lake_query_results") as mock_results:
        mock_results.return_value = {
            "success": True,
            "status": "succeeded",
            "results": [{"event": "test_data"}],
            "results_truncated": False,
            "total_rows_available": 1,
            "column_info": {"order": ["event"], "types": {"event": "string"}},
            "stats": {"bytes_scanned": 1024},
            "has_next_page": True,
            "next_cursor": "next_cursor_456",
            "message": "Query executed successfully",
            "query_id": MOCK_QUERY_ID,
        }

        result = await query_data_lake(test_sql, cursor=cursor, max_rows=50)

    # Verify the function returns success with pagination info
    assert result["success"] is True
    assert result["status"] == "succeeded"
    assert result["has_next_page"] is True
    assert result["next_cursor"] == "next_cursor_456"

    # Verify the cursor was passed to the results function
    mock_results.assert_called_once_with(
        query_id=MOCK_QUERY_ID, max_rows=50, cursor=cursor
    )


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_query_data_lake_first_page_without_cursor(
    mock_graphql_client,
):
    """Test that query_data_lake works without cursor for first page."""
    mock_graphql_client.execute.return_value = {
        "executeDataLakeQuery": {"id": MOCK_QUERY_ID}
    }

    test_sql = (
        "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_occurs_since('1 d')"
    )

    # Mock the query results function to return first page response
    with patch(f"{DATA_LAKE_MODULE_PATH}._get_data_lake_query_results") as mock_results:
        mock_results.return_value = {
            "success": True,
            "status": "succeeded",
            "results": [{"event": "test_data"}],
            "results_truncated": False,
            "total_rows_available": 1,
            "column_info": {"order": ["event"], "types": {"event": "string"}},
            "stats": {"bytes_scanned": 1024},
            "has_next_page": False,
            "next_cursor": None,
            "message": "Query executed successfully",
            "query_id": MOCK_QUERY_ID,
        }

        result = await query_data_lake(test_sql, max_rows=100)

    # Verify the function returns success with first page info
    assert result["success"] is True
    assert result["status"] == "succeeded"
    assert result["has_next_page"] is False
    assert result["next_cursor"] is None

    # Verify no cursor was passed to the results function
    mock_results.assert_called_once_with(
        query_id=MOCK_QUERY_ID, max_rows=100, cursor=None
    )


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_query_data_lake_pagination_complete_workflow(
    mock_graphql_client,
):
    """Test complete pagination workflow from first page to last page."""
    mock_graphql_client.execute.return_value = {
        "executeDataLakeQuery": {"id": MOCK_QUERY_ID}
    }

    test_sql = "SELECT eventName FROM panther_logs.public.aws_cloudtrail WHERE p_occurs_since('1 d')"

    # Mock first page response
    with patch(f"{DATA_LAKE_MODULE_PATH}._get_data_lake_query_results") as mock_results:
        # First call - no cursor, has more pages
        mock_results.return_value = {
            "success": True,
            "status": "succeeded",
            "results": [{"eventName": "GetObject"}, {"eventName": "PutObject"}],
            "results_truncated": False,
            "total_rows_available": 2,
            "column_info": {"order": ["eventName"], "types": {"eventName": "string"}},
            "stats": {"bytes_scanned": 1024},
            "has_next_page": True,
            "next_cursor": "page2_cursor",
            "message": "Query executed successfully",
            "query_id": MOCK_QUERY_ID,
        }

        first_page = await query_data_lake(test_sql, max_rows=2)

        # Verify first page response
        assert first_page["success"] is True
        assert first_page["has_next_page"] is True
        assert first_page["next_cursor"] == "page2_cursor"
        assert len(first_page["results"]) == 2

        # Mock second page response
        mock_results.return_value = {
            "success": True,
            "status": "succeeded",
            "results": [{"eventName": "AssumeRole"}],
            "results_truncated": False,
            "total_rows_available": 1,
            "column_info": {"order": ["eventName"], "types": {"eventName": "string"}},
            "stats": {"bytes_scanned": 512},
            "has_next_page": False,
            "next_cursor": None,
            "message": "Query executed successfully",
            "query_id": MOCK_QUERY_ID,
        }

        second_page = await query_data_lake(test_sql, cursor="page2_cursor", max_rows=2)

        # Verify second page response (last page)
        assert second_page["success"] is True
        assert second_page["has_next_page"] is False
        assert second_page["next_cursor"] is None
        assert len(second_page["results"]) == 1


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_query_data_lake_legacy_truncation_behavior(
    mock_graphql_client,
):
    """Test legacy truncation behavior for non-paginated requests."""
    mock_graphql_client.execute.return_value = {
        "executeDataLakeQuery": {"id": MOCK_QUERY_ID}
    }

    test_sql = (
        "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_occurs_since('1 d')"
    )

    # Mock response that would exceed max_rows
    with patch(f"{DATA_LAKE_MODULE_PATH}._get_data_lake_query_results") as mock_results:
        mock_results.return_value = {
            "success": True,
            "status": "succeeded",
            "results": [{"event": f"data_{i}"} for i in range(5)],  # 5 results
            "results_truncated": True,  # Would be truncated to 3
            "total_rows_available": 5,
            "column_info": {"order": ["event"], "types": {"event": "string"}},
            "stats": {"bytes_scanned": 2048},
            "has_next_page": True,
            "next_cursor": "truncated_cursor",
            "message": "Query executed successfully",
            "query_id": MOCK_QUERY_ID,
        }

        result = await query_data_lake(test_sql, max_rows=3)  # No cursor = legacy mode

        # Verify truncation behavior is preserved
        assert result["success"] is True
        assert result["results_truncated"] is True
        assert result["total_rows_available"] == 5
        assert result["has_next_page"] is True


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_query_data_lake_pagination_with_empty_results(
    mock_graphql_client,
):
    """Test pagination behavior when query returns no results."""
    mock_graphql_client.execute.return_value = {
        "executeDataLakeQuery": {"id": MOCK_QUERY_ID}
    }

    test_sql = "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_occurs_since('1 d') AND eventName = 'NonExistentEvent'"

    with patch(f"{DATA_LAKE_MODULE_PATH}._get_data_lake_query_results") as mock_results:
        mock_results.return_value = {
            "success": True,
            "status": "succeeded",
            "results": [],
            "results_truncated": False,
            "total_rows_available": 0,
            "column_info": {"order": [], "types": {}},
            "stats": {"bytes_scanned": 0},
            "has_next_page": False,
            "next_cursor": None,
            "message": "Query executed successfully",
            "query_id": MOCK_QUERY_ID,
        }

        result = await query_data_lake(test_sql, max_rows=10)

        # Verify empty results handling
        assert result["success"] is True
        assert result["results"] == []
        assert result["has_next_page"] is False
        assert result["next_cursor"] is None
        assert result["results_truncated"] is False
        assert result["total_rows_available"] == 0


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_query_data_lake_max_rows_parameter_limits(
    mock_graphql_client,
):
    """Test that max_rows parameter respects limits and defaults."""
    mock_graphql_client.execute.return_value = {
        "executeDataLakeQuery": {"id": MOCK_QUERY_ID}
    }

    test_sql = (
        "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_occurs_since('1 d')"
    )

    with patch(f"{DATA_LAKE_MODULE_PATH}._get_data_lake_query_results") as mock_results:
        mock_results.return_value = {
            "success": True,
            "status": "succeeded",
            "results": [{"event": "test"}],
            "results_truncated": False,
            "total_rows_available": 1,
            "column_info": {"order": ["event"], "types": {"event": "string"}},
            "stats": {"bytes_scanned": 100},
            "has_next_page": False,
            "next_cursor": None,
            "message": "Query executed successfully",
            "query_id": MOCK_QUERY_ID,
        }

        # Test default max_rows (should be 100)
        await query_data_lake(test_sql)
        mock_results.assert_called_with(
            query_id=MOCK_QUERY_ID, max_rows=100, cursor=None
        )

        # Test custom max_rows
        await query_data_lake(test_sql, max_rows=50)
        mock_results.assert_called_with(
            query_id=MOCK_QUERY_ID, max_rows=50, cursor=None
        )

        # Test with cursor
        await query_data_lake(test_sql, max_rows=25, cursor="test_cursor")
        mock_results.assert_called_with(
            query_id=MOCK_QUERY_ID, max_rows=25, cursor="test_cursor"
        )
