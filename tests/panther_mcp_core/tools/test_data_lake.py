import pytest

from tests.utils.helpers import patch_graphql_client, patch_execute_query

from mcp_panther.panther_mcp_core.tools.data_lake import (
    get_sample_log_events,
    execute_data_lake_query,
)

DATA_LAKE_MODULE_PATH = "mcp_panther.panther_mcp_core.tools.data_lake"

MOCK_QUERY_ID = "query-123456789"

@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_get_sample_log_events_success(mock_graphql_client):
    """Test successful retrieval of sample log events."""
    mock_graphql_client.execute.return_value = {"executeDataLakeQuery": {"id": MOCK_QUERY_ID}}

    result = await get_sample_log_events("AWS.CloudTrail")

    assert result["success"] is True
    assert result["query_id"] == MOCK_QUERY_ID

    mock_graphql_client.execute.assert_called_once()
    call_args = mock_graphql_client.execute.call_args[1]["variable_values"]
    assert "panther_logs.public" in call_args["input"]["databaseName"]
    assert "AWS.CloudTrail" in call_args["input"]["sql"]
    assert "p_event_time" in call_args["input"]["sql"]
    assert "LIMIT 10" in call_args["input"]["sql"]

@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_get_sample_log_events_error(mock_graphql_client):
    """Test handling of errors when getting sample log events."""
    mock_graphql_client.execute.side_effect = Exception("Test error")

    result = await get_sample_log_events("AWS.CloudTrail")

    assert result["success"] is False
    assert "Failed to execute data lake query" in result["message"]
    assert "Test error" in result["message"]

@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_get_sample_log_events_no_query_id(mock_graphql_client):
    """Test handling when no query ID is returned."""
    mock_graphql_client.execute.return_value = {}

    result = await get_sample_log_events("AWS.CloudTrail")

    assert result["success"] is False
    assert "No query ID returned" in result["message"]

@pytest.mark.asyncio
@patch_graphql_client(DATA_LAKE_MODULE_PATH)
async def test_execute_data_lake_query_success(mock_graphql_client):
    """Test successful execution of a data lake query."""
    mock_graphql_client.execute.return_value = {"executeDataLakeQuery": {"id": MOCK_QUERY_ID}}

    sql = "SELECT * FROM panther_logs.public.AWS_CloudTrail LIMIT 10"
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
    mock_graphql_client.execute.return_value = {"executeDataLakeQuery": {"id": MOCK_QUERY_ID}}

    sql = "SELECT * FROM my_custom_table LIMIT 10"
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

    sql = "SELECT * FROM panther_logs.public.AWS_CloudTrail LIMIT 10"
    result = await execute_data_lake_query(sql)

    assert result["success"] is False
    assert "Failed to execute data lake query" in result["message"] 
