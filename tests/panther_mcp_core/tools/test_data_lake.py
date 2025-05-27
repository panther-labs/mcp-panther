import pytest

from mcp_panther.panther_mcp_core.tools.data_lake import (
    _is_name_normalized,
    _normalize_name,
    execute_data_lake_query,
    get_sample_log_events,
)
from tests.utils.helpers import patch_graphql_client

DATA_LAKE_MODULE_PATH = "mcp_panther.panther_mcp_core.tools.data_lake"

MOCK_QUERY_ID = "query-123456789"


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_get_sample_log_events_success(mock_graphql_client):
    """Test successful retrieval of sample log events."""
    mock_graphql_client.execute.return_value = {
        "executeDataLakeQuery": {"id": MOCK_QUERY_ID}
    }

    result = await get_sample_log_events(schema_name="AWS.CloudTrail")

    assert result["success"] is True
    assert result["query_id"] == MOCK_QUERY_ID

    mock_graphql_client.execute.assert_called_once()
    call_args = mock_graphql_client.execute.call_args[1]["variable_values"]
    assert "panther_logs.public" in call_args["input"]["databaseName"]
    assert "AWS_CloudTrail" in call_args["input"]["sql"]
    assert "p_event_time" in call_args["input"]["sql"]
    assert "LIMIT 10" in call_args["input"]["sql"]


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_get_sample_log_events_error(mock_graphql_client):
    """Test handling of errors when getting sample log events."""
    mock_graphql_client.execute.side_effect = Exception("Test error")

    result = await get_sample_log_events(schema_name="AWS.CloudTrail")

    assert result["success"] is False
    assert "Failed to execute data lake query" in result["message"]
    assert "Test error" in result["message"]


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_get_sample_log_events_no_query_id(mock_graphql_client):
    """Test handling when no query ID is returned."""
    mock_graphql_client.execute.return_value = {}

    result = await get_sample_log_events(schema_name="AWS.CloudTrail")

    assert result["success"] is False
    assert "No query ID returned" in result["message"]


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_execute_data_lake_query_success(mock_graphql_client):
    """Test successful execution of a data lake query."""
    mock_graphql_client.execute.return_value = {
        "executeDataLakeQuery": {"id": MOCK_QUERY_ID}
    }

    sql = "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_event_time >= DATEADD(day, -30, CURRENT_TIMESTAMP()) LIMIT 10"
    result = await execute_data_lake_query(sql)

    assert result["success"] is True
    assert result["query_id"] == MOCK_QUERY_ID

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
    result = await execute_data_lake_query(sql, database_name=custom_db)

    assert result["success"] is True

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
        "Query must include p_event_time as a filter condition after WHERE or AND"
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

    for sql in valid_queries:
        result = await execute_data_lake_query(sql)
        assert result["success"] is True, f"Query failed: {sql}"
        assert result["query_id"] == MOCK_QUERY_ID
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
            "Query must include p_event_time as a filter condition after WHERE or AND"
            in result["message"]
        )
        mock_graphql_client.execute.assert_not_called()


def test_normalize_name():
    test_cases = [
        {"input": "@foo", "expected": "at_sign_foo"},
        {"input": "CrAzY-tAbLe", "expected": "CrAzY-tAbLe"},
        {"input": "U2", "expected": "U2"},
        {"input": "2LEGIT-2QUIT", "expected": "two_LEGIT-2QUIT"},
        {"input": "foo,bar", "expected": "foo_comma_bar"},
        {"input": "`foo`", "expected": "backtick_foo_backtick"},
        {"input": "'foo'", "expected": "apostrophe_foo_apostrophe"},
        {"input": "foo.bar", "expected": "foo_bar"},
        {"input": "AWS.CloudTrail", "expected": "AWS_CloudTrail"},
        {"input": ".foo", "expected": "_foo"},
        {"input": "foo-bar", "expected": "foo-bar"},
        {"input": "$foo", "expected": "dollar_sign_foo"},
        {"input": "Μύκονοοοος", "expected": "Mykonoooos"},
        {"input": "fooʼn", "expected": "foo_n"},
        {"input": "foo\\bar", "expected": "foo_backslash_bar"},
        {"input": "<foo>bar", "expected": "_foo_bar"},
    ]

    for tc in test_cases:
        col_name = _normalize_name(tc["input"])
        assert col_name == tc["expected"], (
            f"Input: {tc['input']}, Expected: {tc['expected']}, Got: {col_name}"
        )


def test_is_normalized():
    test_cases = [
        {"input": "@foo", "expected": False},
        {"input": "CrAzY-tAbLe", "expected": True},
        {"input": "U2", "expected": True},
        {"input": "2LEGIT-2QUIT", "expected": False},
        {"input": "foo,bar", "expected": False},
        {"input": "`foo`", "expected": False},
        {"input": "'foo'", "expected": False},
        {"input": "foo.bar", "expected": False},
        {"input": ".foo", "expected": False},
        {"input": "foo-bar", "expected": True},
        {"input": "foo_bar", "expected": True},
        {"input": "$foo", "expected": False},
        {"input": "Μύκονοοοος", "expected": False},
        {"input": "fooʼn", "expected": False},
        {"input": "foo\\bar", "expected": False},
        {"input": "<foo>bar", "expected": False},
    ]

    for tc in test_cases:
        result = _is_name_normalized(tc["input"])
        assert result == tc["expected"], (
            f"Input: {tc['input']}, Expected:  {tc['expected']}, Got: {result}"
        )
