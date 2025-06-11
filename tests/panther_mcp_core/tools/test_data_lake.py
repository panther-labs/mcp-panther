import os
from unittest.mock import patch

import pytest

from mcp_panther.panther_mcp_core.tools.data_lake import (
    DatastoreType,
    QueryStatus,
    _convert_database_references_in_sql,
    _is_name_normalized,
    _normalize_name,
    _validate_and_wrap_reserved_words,
    _validate_fully_qualified_tables,
    cancel_data_lake_query,
    execute_data_lake_query,
    format_database_reference,
    get_current_timestamp_function,
    get_datastore_type,
    get_dateadd_function,
    get_query_syntax_help,
    get_reserved_words_info,
    get_sample_log_events,
    list_data_lake_queries,
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
    # Database name should be formatted based on current datastore (defaults to Snowflake)
    assert call_args["input"]["databaseName"] == "panther_logs.public"
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

    sql = "SELECT * FROM custom_database.my_custom_table WHERE p_event_time >= DATEADD(day, -30, CURRENT_TIMESTAMP()) LIMIT 10"
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
            "input": "SELECT current_user FROM table WHERE p_event_time >= '2024-01-01'",
            "description": "CURRENT_USER cannot be used as column name",
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


# Datastore-specific tests
def test_get_datastore_type_default():
    """Test that datastore type defaults to Snowflake."""
    with patch.dict(os.environ, {}, clear=True):
        result = get_datastore_type()
        assert result == DatastoreType.SNOWFLAKE


def test_get_datastore_type_snowflake():
    """Test explicit Snowflake datastore type."""
    with patch.dict(os.environ, {"PANTHER_DATASTORE_TYPE": "snowflake"}):
        result = get_datastore_type()
        assert result == DatastoreType.SNOWFLAKE


def test_get_datastore_type_redshift():
    """Test explicit Redshift datastore type."""
    with patch.dict(os.environ, {"PANTHER_DATASTORE_TYPE": "redshift"}):
        result = get_datastore_type()
        assert result == DatastoreType.REDSHIFT


def test_get_datastore_type_case_insensitive():
    """Test that datastore type environment variable is case-insensitive."""
    test_cases = ["SNOWFLAKE", "Snowflake", "REDSHIFT", "Redshift"]

    for env_value in test_cases:
        with patch.dict(os.environ, {"PANTHER_DATASTORE_TYPE": env_value}):
            result = get_datastore_type()
            expected = (
                DatastoreType.SNOWFLAKE
                if "snow" in env_value.lower()
                else DatastoreType.REDSHIFT
            )
            assert result == expected


def test_get_datastore_type_invalid():
    """Test that invalid datastore type defaults to Snowflake."""
    with patch.dict(os.environ, {"PANTHER_DATASTORE_TYPE": "invalid"}):
        result = get_datastore_type()
        assert result == DatastoreType.SNOWFLAKE


def test_format_database_reference_snowflake():
    """Test database reference formatting for Snowflake."""
    with patch.dict(os.environ, {"PANTHER_DATASTORE_TYPE": "snowflake"}):
        # Snowflake should preserve .public
        assert format_database_reference("panther_logs.public") == "panther_logs.public"
        assert (
            format_database_reference("panther_signals.public")
            == "panther_signals.public"
        )
        assert format_database_reference("custom_db") == "custom_db"


def test_format_database_reference_redshift():
    """Test database reference formatting for Redshift."""
    with patch.dict(os.environ, {"PANTHER_DATASTORE_TYPE": "redshift"}):
        # Redshift should remove .public
        assert format_database_reference("panther_logs.public") == "panther_logs"
        assert format_database_reference("panther_signals.public") == "panther_signals"
        assert format_database_reference("custom_db") == "custom_db"
        assert format_database_reference("custom_db.public") == "custom_db"


def test_get_reserved_words_info_snowflake():
    """Test reserved words info for Snowflake."""
    with patch.dict(os.environ, {"PANTHER_DATASTORE_TYPE": "snowflake"}):
        result = get_reserved_words_info()

        assert result["datastore_type"] == "snowflake"
        assert "REGEXP" in result["quotable_reserved_words"]  # Snowflake-specific
        assert "QUALIFY" in result["quotable_reserved_words"]  # Snowflake-specific
        assert "COLUMN" in result["quotable_reserved_words"]  # ANSI reserved
        assert "FALSE" in result["forbidden_scalar_expressions"]
        assert "CURRENT_USER" in result["forbidden_column_names"]


def test_get_reserved_words_info_redshift():
    """Test reserved words info for Redshift."""
    with patch.dict(os.environ, {"PANTHER_DATASTORE_TYPE": "redshift"}):
        result = get_reserved_words_info()

        assert result["datastore_type"] == "redshift"
        assert "DELTA" in result["quotable_reserved_words"]  # Redshift-specific
        assert "ANALYZE" in result["quotable_reserved_words"]  # Redshift-specific
        assert "COLUMN" in result["quotable_reserved_words"]  # ANSI reserved
        # Snowflake-specific words should not be in Redshift list
        assert "REGEXP" not in result["quotable_reserved_words"]
        assert "QUALIFY" not in result["quotable_reserved_words"]


def test_validate_and_wrap_reserved_words_redshift():
    """Test reserved words validation for Redshift-specific words."""
    with patch.dict(os.environ, {"PANTHER_DATASTORE_TYPE": "redshift"}):
        # Redshift-specific reserved words should be quoted
        result, error = _validate_and_wrap_reserved_words(
            "SELECT delta, analyze FROM table WHERE p_event_time >= '2024-01-01'"
        )
        assert error is None
        assert '"delta"' in result
        assert '"analyze"' in result

        # Snowflake-specific words should NOT be quoted in Redshift mode
        result, error = _validate_and_wrap_reserved_words(
            "SELECT regexp, qualify FROM table WHERE p_event_time >= '2024-01-01'"
        )
        assert error is None
        assert '"regexp"' not in result  # Should not be quoted in Redshift
        assert '"qualify"' not in result  # Should not be quoted in Redshift


def test_current_timestamp_function():
    """Test datastore-specific timestamp functions."""
    with patch.dict(os.environ, {"PANTHER_DATASTORE_TYPE": "snowflake"}):
        assert get_current_timestamp_function() == "CURRENT_TIMESTAMP()"

    with patch.dict(os.environ, {"PANTHER_DATASTORE_TYPE": "redshift"}):
        assert get_current_timestamp_function() == "GETDATE()"


def test_dateadd_function():
    """Test datastore-specific date addition functions."""
    with patch.dict(os.environ, {"PANTHER_DATASTORE_TYPE": "snowflake"}):
        assert (
            get_dateadd_function("day", -7, "CURRENT_TIMESTAMP()")
            == "DATEADD(day, -7, CURRENT_TIMESTAMP())"
        )
        assert get_dateadd_function("hour", 1, "NOW()") == "DATEADD(hour, 1, NOW())"

    with patch.dict(os.environ, {"PANTHER_DATASTORE_TYPE": "redshift"}):
        assert (
            get_dateadd_function("day", -7, "GETDATE()")
            == "GETDATE() - INTERVAL '7 day'"
        )
        assert get_dateadd_function("hour", 1, "NOW()") == "NOW() + INTERVAL '1 hour'"


def test_fixed_current_date_forbidden_words():
    """Test that CURRENT_DATE is now allowed in WHERE clauses."""
    # CURRENT_DATE should be allowed in WHERE clauses now
    result, error = _validate_and_wrap_reserved_words(
        "SELECT actionName FROM table WHERE p_event_time >= CURRENT_DATE - INTERVAL '30 days'"
    )
    assert error is None
    assert "CURRENT_DATE" in result  # Should be preserved, not cause error


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_execute_data_lake_query_redshift_database_formatting(
    mock_graphql_client,
):
    """Test that database names are formatted correctly for Redshift."""
    with patch.dict(os.environ, {"PANTHER_DATASTORE_TYPE": "redshift"}):
        mock_graphql_client.execute.return_value = {
            "executeDataLakeQuery": {"id": MOCK_QUERY_ID}
        }

        sql = "SELECT * FROM panther_logs.public.test_table WHERE p_event_time >= DATEADD(day, -1, CURRENT_TIMESTAMP())"
        result = await execute_data_lake_query(sql, database_name="panther_logs.public")

        assert result["success"] is True

        # Verify database name was formatted for Redshift (removed .public)
        call_args = mock_graphql_client.execute.call_args[1]["variable_values"]
        assert call_args["input"]["databaseName"] == "panther_logs"


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_get_sample_log_events_redshift_database_formatting(mock_graphql_client):
    """Test that get_sample_log_events formats database names correctly for Redshift."""
    with patch.dict(os.environ, {"PANTHER_DATASTORE_TYPE": "redshift"}):
        mock_graphql_client.execute.return_value = {
            "executeDataLakeQuery": {"id": MOCK_QUERY_ID}
        }

        result = await get_sample_log_events(schema_name="AWS.CloudTrail")

        assert result["success"] is True

        # Verify the SQL uses Redshift formatting (no .public in table reference)
        call_args = mock_graphql_client.execute.call_args[1]["variable_values"]
        sql = call_args["input"]["sql"]
        assert "FROM panther_logs.AWS_CloudTrail" in sql  # No .public
        assert call_args["input"]["databaseName"] == "panther_logs"  # No .public


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


def test_validate_fully_qualified_tables():
    """Test validation of fully qualified table references."""
    # Valid cases - should return None (no error)
    valid_queries = [
        "SELECT * FROM panther_logs.aws_cloudtrail WHERE p_event_time >= '2024-01-01'",
        "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_event_time >= '2024-01-01'",
        "SELECT * FROM panther_signals.public.correlation_signals WHERE p_event_time >= '2024-01-01'",
        "SELECT * FROM db1.table1 JOIN db2.table2 ON db1.table1.id = db2.table2.id WHERE p_event_time >= '2024-01-01'",
    ]

    for sql in valid_queries:
        result = _validate_fully_qualified_tables(sql)
        assert result is None, f"Valid query should not have error: {sql}"

    # Invalid cases - should return error messages
    invalid_queries = [
        "SELECT * FROM aws_cloudtrail WHERE p_event_time >= '2024-01-01'",
        "SELECT * FROM table1 JOIN panther_logs.table2 ON table1.id = table2.id WHERE p_event_time >= '2024-01-01'",
        "SELECT * FROM panther_logs.table1 JOIN table2 ON table1.id = table2.id WHERE p_event_time >= '2024-01-01'",
    ]

    for sql in invalid_queries:
        result = _validate_fully_qualified_tables(sql)
        assert result is not None, f"Invalid query should have error: {sql}"
        assert "not fully qualified" in result


def test_convert_database_references_snowflake():
    """Test database reference conversion for Snowflake (should preserve as-is)."""
    with patch.dict(os.environ, {"PANTHER_DATASTORE_TYPE": "snowflake"}):
        test_cases = [
            {
                "input": "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_event_time >= '2024-01-01'",
                "expected": "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_event_time >= '2024-01-01'",
            },
            {
                "input": "SELECT * FROM panther_logs.aws_cloudtrail WHERE p_event_time >= '2024-01-01'",
                "expected": "SELECT * FROM panther_logs.aws_cloudtrail WHERE p_event_time >= '2024-01-01'",
            },
        ]

        for case in test_cases:
            result = _convert_database_references_in_sql(case["input"])
            assert result == case["expected"]


def test_convert_database_references_redshift():
    """Test database reference conversion for Redshift (should remove .public)."""
    with patch.dict(os.environ, {"PANTHER_DATASTORE_TYPE": "redshift"}):
        test_cases = [
            {
                "input": "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_event_time >= '2024-01-01'",
                "expected": "SELECT * FROM panther_logs.aws_cloudtrail WHERE p_event_time >= '2024-01-01'",
            },
            {
                "input": "SELECT * FROM panther_signals.public.correlation_signals WHERE p_event_time >= '2024-01-01'",
                "expected": "SELECT * FROM panther_signals.correlation_signals WHERE p_event_time >= '2024-01-01'",
            },
            {
                "input": "SELECT * FROM panther_logs.aws_cloudtrail WHERE p_event_time >= '2024-01-01'",
                "expected": "SELECT * FROM panther_logs.aws_cloudtrail WHERE p_event_time >= '2024-01-01'",
            },
        ]

        for case in test_cases:
            result = _convert_database_references_in_sql(case["input"])
            assert result == case["expected"]


def test_get_query_syntax_help_snowflake():
    """Test query syntax help for Snowflake."""
    with patch.dict(os.environ, {"PANTHER_DATASTORE_TYPE": "snowflake"}):
        result = get_query_syntax_help()

        assert result["datastore_type"] == "snowflake"
        assert (
            "REQUIRED: Use fully qualified table references"
            in result["database_references"]
        )
        assert "preserved for Snowflake" in result["database_references"]
        assert "CURRENT_TIMESTAMP()" in result["date_functions"]
        assert "DATEADD" in result["date_functions"]


def test_get_query_syntax_help_redshift():
    """Test query syntax help for Redshift."""
    with patch.dict(os.environ, {"PANTHER_DATASTORE_TYPE": "redshift"}):
        result = get_query_syntax_help()

        assert result["datastore_type"] == "redshift"
        assert (
            "REQUIRED: Use fully qualified table references"
            in result["database_references"]
        )
        assert (
            "automatically converted to remove .public" in result["database_references"]
        )
        assert "GETDATE()" in result["date_functions"]
        assert "INTERVAL" in result["date_functions"]


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_execute_data_lake_query_fully_qualified_validation(mock_graphql_client):
    """Test that execute_data_lake_query validates fully qualified table references."""
    # Query without fully qualified table reference should fail
    sql = "SELECT * FROM aws_cloudtrail WHERE p_event_time >= DATEADD(day, -1, CURRENT_TIMESTAMP())"
    result = await execute_data_lake_query(sql)

    assert result["success"] is False
    assert "not fully qualified" in result["message"]

    # GraphQL client should not be called since validation failed
    mock_graphql_client.execute.assert_not_called()


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_execute_data_lake_query_database_reference_conversion(
    mock_graphql_client,
):
    """Test that database references are converted in SQL queries."""
    with patch.dict(os.environ, {"PANTHER_DATASTORE_TYPE": "redshift"}):
        mock_graphql_client.execute.return_value = {
            "executeDataLakeQuery": {"id": MOCK_QUERY_ID}
        }

        # Query with .public should be converted for Redshift
        sql = "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_event_time >= DATEADD(day, -1, CURRENT_TIMESTAMP())"
        result = await execute_data_lake_query(sql)

        assert result["success"] is True

        # Verify the SQL was converted (removed .public)
        call_args = mock_graphql_client.execute.call_args[1]["variable_values"]
        modified_sql = call_args["input"]["sql"]
        assert "panther_logs.aws_cloudtrail" in modified_sql
        assert "panther_logs.public.aws_cloudtrail" not in modified_sql


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_list_data_lake_queries_success(mock_graphql_client):
    """Test successful listing of data lake queries."""
    mock_response = {
        "dataLakeQueries": {
            "edges": [
                {
                    "node": {
                        "id": "query1",
                        "sql": "SELECT * FROM panther_logs.aws_cloudtrail",
                        "name": "Test Query",
                        "status": "running",
                        "message": "Query executing",
                        "startedAt": "2024-01-01T10:00:00Z",
                        "completedAt": None,
                        "isScheduled": False,
                        "issuedBy": {
                            "id": "user1",
                            "email": "test@example.com",
                            "givenName": "John",
                            "familyName": "Doe",
                        },
                    }
                },
                {
                    "node": {
                        "id": "query2",
                        "sql": "SELECT COUNT(*) FROM panther_logs.aws_cloudtrail",
                        "name": None,
                        "status": "succeeded",
                        "message": "Query completed successfully",
                        "startedAt": "2024-01-01T09:00:00Z",
                        "completedAt": "2024-01-01T09:05:00Z",
                        "isScheduled": True,
                        "issuedBy": {
                            "id": "token1",
                            "name": "API Token 1",
                        },
                    }
                },
            ],
            "pageInfo": {
                "hasNextPage": False,
                "endCursor": None,
                "hasPreviousPage": False,
                "startCursor": None,
            },
        }
    }
    mock_graphql_client.execute.return_value = mock_response

    result = await list_data_lake_queries()

    assert result["success"] is True
    assert len(result["queries"]) == 2

    # Check first query (user-issued)
    query1 = result["queries"][0]
    assert query1["id"] == "query1"
    assert query1["status"] == "running"
    assert query1["is_scheduled"] is False
    assert query1["issued_by"]["type"] == "user"
    assert query1["issued_by"]["email"] == "test@example.com"

    # Check second query (API token-issued)
    query2 = result["queries"][1]
    assert query2["id"] == "query2"
    assert query2["status"] == "succeeded"
    assert query2["is_scheduled"] is True
    assert query2["issued_by"]["type"] == "api_token"
    assert query2["issued_by"]["name"] == "API Token 1"


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_list_data_lake_queries_with_filters(mock_graphql_client):
    """Test listing data lake queries with filters."""
    mock_graphql_client.execute.return_value = {
        "dataLakeQueries": {"edges": [], "pageInfo": {}}
    }

    # Test with status filter
    await list_data_lake_queries(status=[QueryStatus.RUNNING, QueryStatus.FAILED])

    call_args = mock_graphql_client.execute.call_args[1]["variable_values"]
    assert call_args["input"]["status"] == ["running", "failed"]


# Remove this test since we now use enums for validation


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_list_data_lake_queries_error(mock_graphql_client):
    """Test error handling when listing data lake queries fails."""
    mock_graphql_client.execute.side_effect = Exception("GraphQL error")

    result = await list_data_lake_queries()

    assert result["success"] is False
    assert "Failed to list data lake queries" in result["message"]


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_cancel_data_lake_query_success(mock_graphql_client):
    """Test successful cancellation of a data lake query."""
    mock_response = {"cancelDataLakeQuery": {"id": "query123"}}
    mock_graphql_client.execute.return_value = mock_response

    result = await cancel_data_lake_query("query123")

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

    result = await cancel_data_lake_query("nonexistent")

    assert result["success"] is False
    assert "not found" in result["message"]
    assert "already completed or been cancelled" in result["message"]


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_cancel_data_lake_query_cannot_cancel(mock_graphql_client):
    """Test cancellation of a query that cannot be cancelled."""
    mock_graphql_client.execute.side_effect = Exception("Query cannot be cancelled")

    result = await cancel_data_lake_query("completed_query")

    assert result["success"] is False
    assert "cannot be cancelled" in result["message"]
    assert "Only running queries" in result["message"]


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_cancel_data_lake_query_permission_error(mock_graphql_client):
    """Test cancellation with permission error."""
    mock_graphql_client.execute.side_effect = Exception("Permission denied")

    result = await cancel_data_lake_query("query123")

    assert result["success"] is False
    assert "Permission denied" in result["message"]


@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_cancel_data_lake_query_no_id_returned(mock_graphql_client):
    """Test cancellation when no ID is returned."""
    mock_response = {"cancelDataLakeQuery": {}}
    mock_graphql_client.execute.return_value = mock_response

    result = await cancel_data_lake_query("query123")

    assert result["success"] is False
    assert "No query ID returned" in result["message"]
