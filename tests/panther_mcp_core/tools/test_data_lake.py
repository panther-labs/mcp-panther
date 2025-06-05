import pytest

from mcp_panther.panther_mcp_core.tools.data_lake import (
    _is_name_normalized,
    _normalize_name,
    _validate_and_wrap_reserved_words,
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


def test_validate_and_wrap_reserved_words():
    """Test that Snowflake reserved words are properly validated and wrapped."""

    # Test cases that should succeed with wrapping
    success_cases = [
        # Non-reserved words should remain unchanged
        {
            "input": "SELECT all_items, order_id FROM table WHERE p_event_time >= '2024-01-01'",
            "expected": "SELECT all_items, order_id FROM table WHERE p_event_time >= '2024-01-01'",
            "description": "Non-reserved words should remain unchanged",
        },
        # Snowflake reserved words that can be quoted
        {
            "input": "SELECT regexp, qualify FROM table WHERE p_event_time >= '2024-01-01'",
            "expected": 'SELECT "regexp", "qualify" FROM table WHERE p_event_time >= \'2024-01-01\'',
            "description": "Snowflake reserved words as columns should be quoted",
        },
        # Additional problematic words that can be quoted
        {
            "input": "SELECT database, schema, view FROM table WHERE p_event_time >= '2024-01-01'",
            "expected": 'SELECT "database", "schema", "view" FROM table WHERE p_event_time >= \'2024-01-01\'',
            "description": "Words that cause issues in SELECT statements should be quoted",
        },
        # Test account as direct column reference (should be quoted)
        {
            "input": "SELECT account, organization, normal_field FROM table WHERE p_event_time >= '2024-01-01'",
            "expected": 'SELECT "account", "organization", normal_field FROM table WHERE p_event_time >= \'2024-01-01\'',
            "description": "ACCOUNT and ORGANIZATION should be quoted when used as direct column references",
        },
        # ANSI reserved words that can be quoted
        {
            "input": "SELECT action, column FROM mytable WHERE p_event_time >= '2024-01-01'",
            "expected": "SELECT action, \"column\" FROM mytable WHERE p_event_time >= '2024-01-01'",
            "description": "COLUMN is reserved (ANSI) and should be quoted, ACTION is not reserved",
        },
        # Mixed reserved and non-reserved
        {
            "input": "SELECT normal_col, action, another_col FROM table WHERE p_event_time >= '2024-01-01'",
            "expected": "SELECT normal_col, action, another_col FROM table WHERE p_event_time >= '2024-01-01'",
            "description": "Only reserved words should be quoted, ACTION is not reserved",
        },
        # Already quoted words should remain unchanged
        {
            "input": "SELECT \"action\", `column` FROM table WHERE p_event_time >= '2024-01-01'",
            "expected": "SELECT \"action\", `column` FROM table WHERE p_event_time >= '2024-01-01'",
            "description": "Already quoted words should remain unchanged",
        },
        # Real-world VPC Flow logs query with mixed reserved/non-reserved words
        {
            "input": """SELECT COUNT(*) as total_rejected_flows, COUNT(DISTINCT srcAddr) as unique_source_ips, COUNT(DISTINCT dstAddr) as unique_dest_ips, COUNT(DISTINCT account) as affected_accounts, SUM(bytes) as total_bytes_rejected, SUM(packets) as total_packets_rejected, -- Most targeted destination addresses
    dstAddr as most_targeted_dest, COUNT(*) as flows_to_dest
FROM panther_logs.public.aws_vpcflow 
WHERE p_event_time >= DATEADD(hour, -4, CURRENT_TIMESTAMP())
  AND action = 'REJECT'
GROUP BY dstAddr
ORDER BY flows_to_dest DESC
LIMIT 10""",
            "expected": """SELECT COUNT(*) as total_rejected_flows, COUNT(DISTINCT srcAddr) as unique_source_ips, COUNT(DISTINCT dstAddr) as unique_dest_ips, COUNT(DISTINCT "account") as affected_accounts, SUM(bytes) as total_bytes_rejected, SUM(packets) as total_packets_rejected, -- Most targeted destination addresses
    dstAddr as most_targeted_dest, COUNT(*) as flows_to_dest
FROM panther_logs.public.aws_vpcflow 
WHERE p_event_time >= DATEADD(hour, -4, CURRENT_TIMESTAMP())
  AND action = 'REJECT'
GROUP BY dstAddr
ORDER BY flows_to_dest DESC
LIMIT 10""",
            "description": "Real-world VPC Flow query: account quoted even in function calls, action not quoted (correct)",
        },
        # CASE WHEN expressions should work (CASE and WHEN are valid in this context)
        {
            "input": "SELECT SUM(CASE WHEN account IS NOT NULL THEN 1 ELSE 0 END) as account_count FROM table WHERE p_event_time >= '2024-01-01'",
            "expected": "SELECT SUM(CASE WHEN \"account\" IS NOT NULL THEN 1 ELSE 0 END) as account_count FROM table WHERE p_event_time >= '2024-01-01'",
            "description": "CASE WHEN expressions should work, with account quoted inside the expression",
        },
    ]

    for tc in success_cases:
        result, error = _validate_and_wrap_reserved_words(tc["input"])
        assert error is None, f"Unexpected error for {tc['description']}: {error}"
        assert result == tc["expected"], (
            f"{tc['description']}\nInput: {tc['input']}\nExpected: {tc['expected']}\nGot: {result}"
        )

    # Test cases that should fail with errors
    error_cases = [
        {
            "input": "SELECT false FROM table WHERE p_event_time >= '2024-01-01'",
            "description": "FALSE cannot be used as column reference in scalar expressions",
            "expected_error": "cannot be used as column reference in scalar expressions",
        },
        {
            "input": "SELECT true, case FROM table WHERE p_event_time >= '2024-01-01'",
            "description": "TRUE and CASE cannot be used as column references",
            "expected_error": "cannot be used as column reference in scalar expressions",
        },
        {
            "input": "SELECT current_date FROM table WHERE p_event_time >= '2024-01-01'",
            "description": "CURRENT_DATE cannot be used as column name",
            "expected_error": "cannot be used as column name (reserved by ANSI)",
        },
    ]

    for tc in error_cases:
        result, error = _validate_and_wrap_reserved_words(tc["input"])
        assert error is not None, (
            f"Expected error for {tc['description']}, but got none"
        )
        assert tc["expected_error"] in error, (
            f"{tc['description']}\nExpected error containing: {tc['expected_error']}\nGot: {error}"
        )


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_execute_data_lake_query_with_quotable_reserved_words(
    mock_graphql_client,
):
    """Test that quotable reserved words are properly wrapped when executing queries."""
    mock_graphql_client.execute.return_value = {
        "executeDataLakeQuery": {"id": MOCK_QUERY_ID}
    }

    # Query with ANSI reserved words that can be quoted as column names
    sql = 'SELECT sourceaddress, "order", "all" FROM panther_logs.public.test_table WHERE p_event_time >= DATEADD(day, -1, CURRENT_TIMESTAMP()) LIMIT 10'
    result = await execute_data_lake_query(sql)

    assert result["success"] is True
    assert result["query_id"] == MOCK_QUERY_ID

    # Verify the query was processed without errors
    call_args = mock_graphql_client.execute.call_args[1]["variable_values"]
    modified_sql = call_args["input"]["sql"]
    assert '"order"' in modified_sql
    assert '"all"' in modified_sql


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_execute_data_lake_query_with_forbidden_words(mock_graphql_client):
    """Test that forbidden reserved words cause query rejection."""
    # Query with forbidden words (FALSE cannot be used as column reference in scalar expressions)
    sql = "SELECT false, true FROM panther_logs.public.test_table WHERE p_event_time >= DATEADD(day, -1, CURRENT_TIMESTAMP()) LIMIT 10"
    result = await execute_data_lake_query(sql)

    assert result["success"] is False
    assert "forbidden keyword usage" in result["message"]
    assert (
        "cannot be used as column reference in scalar expressions" in result["message"]
    )

    # Verify the GraphQL client was not called since validation failed
    mock_graphql_client.execute.assert_not_called()


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_execute_data_lake_query_snowflake_reserved_words(mock_graphql_client):
    """Test that Snowflake-specific reserved words are properly wrapped."""
    mock_graphql_client.execute.return_value = {
        "executeDataLakeQuery": {"id": MOCK_QUERY_ID}
    }

    # Query with Snowflake reserved words that can be quoted
    sql = "SELECT regexp, qualify, minus FROM panther_logs.public.test_table WHERE p_event_time >= DATEADD(day, -1, CURRENT_TIMESTAMP())"
    result = await execute_data_lake_query(sql)

    assert result["success"] is True

    # Verify the query was modified to wrap Snowflake reserved words
    call_args = mock_graphql_client.execute.call_args[1]["variable_values"]
    modified_sql = call_args["input"]["sql"]
    assert '"regexp"' in modified_sql
    assert '"qualify"' in modified_sql
    assert '"minus"' in modified_sql
