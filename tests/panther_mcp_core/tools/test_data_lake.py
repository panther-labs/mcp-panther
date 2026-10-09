from unittest.mock import call, patch

import pytest

from mcp_panther.panther_mcp_core.tools.data_lake import (
    _cancel_data_lake_query,
    query_data_lake,
)
from tests.utils.helpers import patch_execute_query

DATA_LAKE_MODULE_PATH = "mcp_panther.panther_mcp_core.tools.data_lake"

MOCK_QUERY_ID = "query-123456789"


@pytest.mark.asyncio
@patch_execute_query(DATA_LAKE_MODULE_PATH)
async def test_query_data_lake_success(mock_execute_query):
    """Test successful execution of a data lake query."""
    mock_execute_query.return_value = {"executeDataLakeQuery": {"id": MOCK_QUERY_ID}}
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

    mock_execute_query.assert_called_once()
    call_args = mock_execute_query.call_args[0][
        1
    ]  # Second positional arg is variables dict
    assert call_args["input"]["sql"] == sql
    assert call_args["input"]["databaseName"] == "panther_logs.public"


@pytest.mark.asyncio
@patch_execute_query(DATA_LAKE_MODULE_PATH)
async def test_query_data_lake_custom_database(mock_execute_query):
    """Test executing a data lake query with a custom database."""
    mock_execute_query.return_value = {"executeDataLakeQuery": {"id": MOCK_QUERY_ID}}
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

    call_args = mock_execute_query.call_args[0][1]
    assert call_args["input"]["databaseName"] == custom_db


@pytest.mark.asyncio
@patch_execute_query(DATA_LAKE_MODULE_PATH)
async def test_query_data_lake_error(mock_execute_query):
    """Test handling of errors when executing a data lake query."""
    mock_execute_query.side_effect = Exception("Test error")

    sql = "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_event_time >= DATEADD(day, -30, CURRENT_TIMESTAMP()) LIMIT 10"
    result = await query_data_lake(sql)

    assert result["success"] is False
    assert "Failed to execute data lake query" in result["message"]
    assert (
        result["query_id"] is None
    )  # No query_id when error occurs before query execution


@pytest.mark.asyncio
@patch_execute_query(DATA_LAKE_MODULE_PATH)
async def test_query_data_lake_missing_event_time(mock_execute_query):
    """Test that queries without p_event_time filter are rejected."""
    sql = "SELECT * FROM panther_logs.public.aws_cloudtrail LIMIT 10"
    result = await query_data_lake(sql)

    assert result["success"] is False
    assert (
        "Query must include a time filter: either `p_event_time` condition or Panther macro"
        in result["message"]
    )
    assert result["query_id"] is None  # No query_id when validation fails
    mock_execute_query.assert_not_called()


@pytest.mark.asyncio
@patch_execute_query(DATA_LAKE_MODULE_PATH)
async def test_query_data_lake_with_event_time(mock_execute_query):
    """Test that queries with p_event_time filter are accepted."""
    mock_execute_query.return_value = {"executeDataLakeQuery": {"id": MOCK_QUERY_ID}}

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
            mock_execute_query.assert_called_once()
            mock_execute_query.reset_mock()


@pytest.mark.asyncio
@patch_execute_query(DATA_LAKE_MODULE_PATH)
async def test_query_data_lake_invalid_event_time_usage(mock_execute_query):
    """Test that queries with invalid p_event_time usage are rejected."""
    mock_execute_query.return_value = {"executeDataLakeQuery": {"id": MOCK_QUERY_ID}}

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
        mock_execute_query.assert_not_called()


@pytest.mark.asyncio
@patch_execute_query(DATA_LAKE_MODULE_PATH)
async def test_cancel_data_lake_query_success(mock_execute_query):
    """Test successful cancellation of a data lake query."""
    mock_response = {"cancelDataLakeQuery": {"id": "query123"}}
    mock_execute_query.return_value = mock_response

    result = await _cancel_data_lake_query("query123")

    assert result["success"] is True
    assert result["query_id"] == "query123"
    assert "Successfully cancelled" in result["message"]

    # Verify correct GraphQL call
    call_args = mock_execute_query.call_args[0][1]
    assert call_args["input"]["id"] == "query123"


@pytest.mark.asyncio
@patch_execute_query(DATA_LAKE_MODULE_PATH)
async def test_cancel_data_lake_query_not_found(mock_execute_query):
    """Test cancellation of a non-existent query."""
    mock_execute_query.side_effect = Exception("Query not found")

    result = await _cancel_data_lake_query("nonexistent")

    assert result["success"] is False
    assert "not found" in result["message"]
    assert "already completed or been cancelled" in result["message"]


@pytest.mark.asyncio
@patch_execute_query(DATA_LAKE_MODULE_PATH)
async def test_cancel_data_lake_query_cannot_cancel(mock_execute_query):
    """Test cancellation of a query that cannot be cancelled."""
    mock_execute_query.side_effect = Exception("Query cannot be cancelled")

    result = await _cancel_data_lake_query("completed_query")

    assert result["success"] is False
    assert "cannot be cancelled" in result["message"]
    assert "Only running queries" in result["message"]


@pytest.mark.asyncio
@patch_execute_query(DATA_LAKE_MODULE_PATH)
async def test_cancel_data_lake_query_permission_error(mock_execute_query):
    """Test cancellation with permission error."""
    mock_execute_query.side_effect = Exception("Permission denied")

    result = await _cancel_data_lake_query("query123")

    assert result["success"] is False
    assert "Permission denied" in result["message"]


@pytest.mark.asyncio
@patch_execute_query(DATA_LAKE_MODULE_PATH)
async def test_cancel_data_lake_query_no_id_returned(mock_execute_query):
    """Test cancellation when no ID is returned."""
    mock_response = {"cancelDataLakeQuery": {}}
    mock_execute_query.return_value = mock_response

    result = await _cancel_data_lake_query("query123")

    assert result["success"] is False
    assert "No query ID returned" in result["message"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 'null' AS sample_value",
        "SELECT 'create' AS sample_value",
        "SELECT 'NuLl' AS sample_value",
        "SELECT 'ordinary text' AS sample_value",
        "SELECT 'it''s null' AS sample_value",
        r"SELECT 'it\'s create' AS sample_value",
        'SELECT "create", "null", "MixedCase" FROM "sample_table"',
        'SELECT "a""b" FROM "sample_table"',
        "SELECT 'null' AS \"create\", 'create' AS \"null\"",
        "SELECT $$null$$ AS sample_value",
        "SELECT $$create 'null'; \"quoted\"\ntext$$ AS sample_value",
        "SELECT 'null' AS sample_value -- 'create' stays a comment\n",
        "SELECT /* 'null' */ 'create' AS sample_value;\n",
        "SELECT 'table', 'column', 'index' FROM sample_table",
        "SELECT sample_value FROM sample_table WHERE sample_value = 'where'",
        "SELECT sample_value FROM sample_table WHERE event_time > '2024-01-01'",
        "SELECT 'null' AS sample_value FROM panther_logs.public.aws_cloudtrail WHERE p_occurs_since('1 d') LIMIT 1",
        """
    SELECT sample_value AS "select", region AS "from"
    FROM sample_table
    WHERE p_event_time >= CURRENT_TIMESTAMP() - INTERVAL '1 DAY'
    ORDER BY "select", "from"
    """,
    ],
    ids=[
        "null-literal",
        "create-literal",
        "mixed-case-literal",
        "ordinary-literal",
        "doubled-quote-literal",
        "backslash-escaped-literal",
        "quoted-identifiers",
        "escaped-identifier",
        "literals-and-identifiers",
        "dollar-quoted-literal",
        "multiline-dollar-quoted-literal",
        "line-comment",
        "block-comment",
        "reserved-literal-projection",
        "reserved-literal-predicate",
        "date-literal",
        "panther-table-with-time-macro",
        "quoted-aliases-and-interval",
    ],
)
async def test_query_data_lake_preserves_sql(sql):
    """Submit literals and quoted identifiers to the API without rewriting SQL."""
    with (
        patch(f"{DATA_LAKE_MODULE_PATH}._execute_query") as mock_execute_query,
        patch(f"{DATA_LAKE_MODULE_PATH}._get_data_lake_query_results") as mock_results,
        patch(f"{DATA_LAKE_MODULE_PATH}.asyncio.sleep"),
    ):
        mock_execute_query.return_value = {
            "executeDataLakeQuery": {"id": MOCK_QUERY_ID}
        }
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

        result = await query_data_lake(sql)

    assert result["success"] is True
    assert result["status"] == "succeeded"
    assert result["query_id"] == MOCK_QUERY_ID
    mock_execute_query.assert_awaited_once()
    variables = mock_execute_query.call_args.args[1]
    assert variables["input"]["sql"] == sql


@pytest.mark.asyncio
async def test_query_data_lake_preserves_malformed_sql_for_backend_validation():
    """Leave SQL syntax validation to the backend and report its error."""
    sql = "SELECT FROM WHERE ((("
    with patch(f"{DATA_LAKE_MODULE_PATH}._execute_query") as mock_execute_query:
        mock_execute_query.side_effect = Exception("SQL compilation error")
        result = await query_data_lake(sql)

    mock_execute_query.assert_awaited_once()
    assert mock_execute_query.call_args.args[1]["input"]["sql"] == sql
    assert result["success"] is False
    assert "SQL compilation error" in result["message"]
    assert result["query_id"] is None


@pytest.mark.asyncio
@patch_execute_query(DATA_LAKE_MODULE_PATH)
async def test_query_data_lake_rejects_legacy_and_invalid_cursors(mock_execute_query):
    """A cursor without an original query ID must not submit a new query."""
    test_sql = (
        "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_occurs_since('1 d')"
    )
    with patch(f"{DATA_LAKE_MODULE_PATH}._get_data_lake_query_results") as mock_results:
        legacy = await query_data_lake(test_sql, cursor="old-backend-cursor")
        invalid = await query_data_lake(
            test_sql, cursor="mcp-panther-query-page-v1:invalid!"
        )
        non_ascii = await query_data_lake(
            test_sql, cursor="mcp-panther-query-page-v1:é"
        )

    assert legacy["success"] is False
    assert "rerun the query" in legacy["message"]
    assert invalid["success"] is False
    assert "Invalid pagination cursor" in invalid["message"]
    assert non_ascii["success"] is False
    assert "Invalid pagination cursor" in non_ascii["message"]
    mock_execute_query.assert_not_called()
    mock_results.assert_not_called()


@pytest.mark.asyncio
@patch_execute_query(DATA_LAKE_MODULE_PATH)
async def test_query_data_lake_rejects_cursor_for_different_request(mock_execute_query):
    """A page token cannot silently switch to different SQL or a database."""
    mock_execute_query.return_value = {"executeDataLakeQuery": {"id": MOCK_QUERY_ID}}
    sql = "SELECT * FROM panther_logs.public.example WHERE p_occurs_since('1 d')"

    with (
        patch(f"{DATA_LAKE_MODULE_PATH}._get_data_lake_query_results") as mock_results,
        patch(f"{DATA_LAKE_MODULE_PATH}.asyncio.sleep"),
    ):
        mock_results.return_value = {
            "success": True,
            "status": "succeeded",
            "has_next_page": True,
            "next_cursor": "backend-cursor",
            "query_id": MOCK_QUERY_ID,
        }
        first_page = await query_data_lake(sql)
        wrong_sql = await query_data_lake(
            sql + " LIMIT 1", cursor=first_page["next_cursor"]
        )
        wrong_database = await query_data_lake(
            sql, database_name="other_database", cursor=first_page["next_cursor"]
        )

    assert wrong_sql["success"] is False
    assert wrong_database["success"] is False
    assert "does not match" in wrong_sql["message"]
    assert "does not match" in wrong_database["message"]
    mock_execute_query.assert_called_once()
    mock_results.assert_called_once()


@pytest.mark.asyncio
@patch_execute_query(DATA_LAKE_MODULE_PATH)
async def test_query_data_lake_first_page_without_cursor(
    mock_execute_query,
):
    """Test that query_data_lake works without cursor for first page."""
    mock_execute_query.return_value = {"executeDataLakeQuery": {"id": MOCK_QUERY_ID}}

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
@patch_execute_query(DATA_LAKE_MODULE_PATH)
async def test_query_data_lake_pagination_complete_workflow(
    mock_execute_query,
):
    """All pages fetch from the first query instead of submitting SQL again."""
    mock_execute_query.side_effect = [
        {"executeDataLakeQuery": {"id": MOCK_QUERY_ID}},
        {"executeDataLakeQuery": {"id": "unexpected-new-query"}},
    ]

    test_sql = "SELECT eventName, 'null' AS sample_value FROM panther_logs.public.aws_cloudtrail WHERE p_occurs_since('1 d')"

    with (
        patch(f"{DATA_LAKE_MODULE_PATH}._get_data_lake_query_results") as mock_results,
        patch(f"{DATA_LAKE_MODULE_PATH}.asyncio.sleep") as mock_sleep,
    ):
        mock_results.side_effect = [
            {
                "success": True,
                "status": "succeeded",
                "results": [{"eventName": "GetObject"}, {"eventName": "PutObject"}],
                "results_truncated": False,
                "total_rows_available": 2,
                "column_info": {
                    "order": ["eventName"],
                    "types": {"eventName": "string"},
                },
                "stats": {"bytes_scanned": 1024},
                "has_next_page": True,
                "next_cursor": "page2_cursor",
                "message": "Query executed successfully",
                "query_id": MOCK_QUERY_ID,
            },
            {
                "success": True,
                "status": "succeeded",
                "results": [{"eventName": "AssumeRole"}],
                "has_next_page": True,
                "next_cursor": "page3_cursor",
                "query_id": MOCK_QUERY_ID,
            },
            {
                "success": True,
                "status": "succeeded",
                "results": [{"eventName": "DeleteObject"}],
                "has_next_page": False,
                "next_cursor": None,
                "query_id": MOCK_QUERY_ID,
            },
        ]
        first_page = await query_data_lake(test_sql, max_rows=2)
        second_page = await query_data_lake(
            test_sql, cursor=first_page["next_cursor"], max_rows=2
        )
        third_page = await query_data_lake(
            test_sql, cursor=second_page["next_cursor"], max_rows=2
        )

    assert first_page["next_cursor"] != "page2_cursor"
    assert second_page["next_cursor"] != "page3_cursor"
    assert third_page["next_cursor"] is None
    assert [page["results"][0]["eventName"] for page in (second_page, third_page)] == [
        "AssumeRole",
        "DeleteObject",
    ]
    mock_execute_query.assert_awaited_once()
    assert mock_execute_query.call_args.args[1]["input"]["sql"] == test_sql
    mock_sleep.assert_awaited_once()
    assert mock_results.call_args_list == [
        call(query_id=MOCK_QUERY_ID, max_rows=2, cursor=None),
        call(query_id=MOCK_QUERY_ID, max_rows=2, cursor="page2_cursor"),
        call(query_id=MOCK_QUERY_ID, max_rows=2, cursor="page3_cursor"),
    ]


@pytest.mark.asyncio
@patch_execute_query(DATA_LAKE_MODULE_PATH)
async def test_query_data_lake_continuation_failure_passes_through(mock_execute_query):
    """Expired results pass through without another SQL submission or page token."""
    mock_execute_query.return_value = {"executeDataLakeQuery": {"id": MOCK_QUERY_ID}}
    sql = "SELECT 'null' AS sample_value"
    failure = {
        "success": False,
        "status": "failed",
        "message": "Query results have expired",
        "query_id": MOCK_QUERY_ID,
    }

    with (
        patch(f"{DATA_LAKE_MODULE_PATH}._get_data_lake_query_results") as mock_results,
        patch(f"{DATA_LAKE_MODULE_PATH}.asyncio.sleep") as mock_sleep,
    ):
        mock_results.side_effect = [
            {
                "success": True,
                "status": "succeeded",
                "results": [{"sample_value": "null"}],
                "has_next_page": True,
                "next_cursor": "backend-cursor",
                "query_id": MOCK_QUERY_ID,
            },
            failure,
        ]
        first_page = await query_data_lake(sql, max_rows=1)
        result = await query_data_lake(
            sql, cursor=first_page["next_cursor"], max_rows=1
        )

    assert result == failure
    assert "next_cursor" not in result
    mock_execute_query.assert_awaited_once()
    assert mock_execute_query.call_args.args[1]["input"]["sql"] == sql
    assert mock_results.await_args_list == [
        call(query_id=MOCK_QUERY_ID, max_rows=1, cursor=None),
        call(query_id=MOCK_QUERY_ID, max_rows=1, cursor="backend-cursor"),
    ]
    mock_sleep.assert_awaited_once()


@pytest.mark.asyncio
@patch_execute_query(DATA_LAKE_MODULE_PATH)
async def test_query_data_lake_legacy_truncation_behavior(
    mock_execute_query,
):
    """Test legacy truncation behavior for non-paginated requests."""
    mock_execute_query.return_value = {"executeDataLakeQuery": {"id": MOCK_QUERY_ID}}

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
@patch_execute_query(DATA_LAKE_MODULE_PATH)
async def test_query_data_lake_pagination_with_empty_results(
    mock_execute_query,
):
    """Test pagination behavior when query returns no results."""
    mock_execute_query.return_value = {"executeDataLakeQuery": {"id": MOCK_QUERY_ID}}

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
@patch_execute_query(DATA_LAKE_MODULE_PATH)
async def test_query_data_lake_max_rows_parameter_limits(
    mock_execute_query,
):
    """Test that max_rows parameter respects limits and defaults."""
    mock_execute_query.return_value = {"executeDataLakeQuery": {"id": MOCK_QUERY_ID}}

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

        # Continue a page with a different row limit.
        mock_results.return_value = {
            **mock_results.return_value,
            "has_next_page": True,
            "next_cursor": "test_cursor",
        }
        first_page = await query_data_lake(test_sql)
        await query_data_lake(test_sql, max_rows=25, cursor=first_page["next_cursor"])
        mock_results.assert_called_with(
            query_id=MOCK_QUERY_ID, max_rows=25, cursor="test_cursor"
        )
