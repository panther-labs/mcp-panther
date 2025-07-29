import pytest

from mcp_panther.panther_mcp_core.tools.schemas import (
    get_log_type_schema_details,
    list_log_type_schemas,
)
from tests.utils.helpers import patch_graphql_client

MOCK_SCHEMA = {
    "name": "AWS.CloudTrail",
    "description": "CloudTrail logs provide visibility into actions taken by a user, role, or an AWS service in CloudTrail.",
    "revision": 564,
    "isArchived": False,
    "isManaged": True,
    "referenceURL": "https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-event-reference.html",
    "createdAt": "2021-07-16T18:46:35.154956402Z",
    "updatedAt": "2025-07-28T15:13:12.468559184Z",
}

MOCK_SCHEMA_DETAILED = {
    **MOCK_SCHEMA,
    "spec": "version: 0\nfields:\n  - name: eventTime\n    type: timestamp\n    description: The date and time the event occurred",
    "version": 1,
    "isFieldDiscoveryEnabled": True,
    "discoveredSpec": "version: 0\nfields:\n  - name: eventTime\n    type: timestamp",
}

MOCK_SCHEMA_GCP = {
    "name": "GCP.AuditLog",
    "description": "Google Cloud Audit Logs provide visibility into administrative activities and access to your Google Cloud resources.",
    "revision": 123,
    "isArchived": False,
    "isManaged": True,
    "referenceURL": "https://cloud.google.com/logging/docs/audit",
    "createdAt": "2021-07-16T18:46:35.340050885Z",
    "updatedAt": "2025-07-28T15:13:12.756134109Z",
}

MOCK_SCHEMAS_RESPONSE = {
    "schemas": {
        "edges": [
            {"node": MOCK_SCHEMA},
            {"node": MOCK_SCHEMA_GCP},
        ]
    }
}

MOCK_SCHEMA_DETAILS_RESPONSE = {
    "schemas": {
        "edges": [
            {"node": MOCK_SCHEMA_DETAILED},
        ]
    }
}

SCHEMAS_MODULE_PATH = "mcp_panther.panther_mcp_core.tools.schemas"


@pytest.mark.asyncio
@patch_graphql_client(SCHEMAS_MODULE_PATH)
async def test_list_log_type_schemas_success(mock_client):
    """Test successful listing of log type schemas."""
    mock_client.execute.return_value = MOCK_SCHEMAS_RESPONSE

    result = await list_log_type_schemas()

    assert result["success"] is True
    assert len(result["schemas"]) == 2
    assert result["schemas"][0]["name"] == "AWS.CloudTrail"
    assert result["schemas"][1]["name"] == "GCP.AuditLog"
    mock_client.execute.assert_called_once()


@pytest.mark.asyncio
@patch_graphql_client(SCHEMAS_MODULE_PATH)
async def test_list_log_type_schemas_with_filters(mock_client):
    """Test listing log type schemas with filters."""
    mock_client.execute.return_value = MOCK_SCHEMAS_RESPONSE

    result = await list_log_type_schemas(
        contains="AWS", is_archived=True, is_in_use=True, is_managed=True
    )

    assert result["success"] is True
    # Verify the input variables were passed correctly
    call_args = mock_client.execute.call_args
    variables = call_args[1]["variable_values"]["input"]
    assert variables["contains"] == "AWS"
    assert variables["isArchived"] is True
    assert variables["isInUse"] is True
    assert variables["isManaged"] is True


@pytest.mark.asyncio
@patch_graphql_client(SCHEMAS_MODULE_PATH)
async def test_list_log_type_schemas_no_data(mock_client):
    """Test handling when no schemas data is returned."""
    mock_client.execute.return_value = {}

    result = await list_log_type_schemas()

    assert result["success"] is False
    assert "No schemas data returned" in result["message"]


@pytest.mark.asyncio
@patch_graphql_client(SCHEMAS_MODULE_PATH)
async def test_list_log_type_schemas_exception(mock_client):
    """Test handling of exceptions during schema listing."""
    mock_client.execute.side_effect = Exception("GraphQL error")

    result = await list_log_type_schemas()

    assert result["success"] is False
    assert "Failed to fetch schemas" in result["message"]
    assert "GraphQL error" in result["message"]


@pytest.mark.asyncio
@patch_graphql_client(SCHEMAS_MODULE_PATH)
async def test_get_log_type_schema_details_success(mock_client):
    """Test successful retrieval of detailed schema information."""
    mock_client.execute.return_value = MOCK_SCHEMA_DETAILS_RESPONSE

    result = await get_log_type_schema_details(["AWS.CloudTrail"])

    assert result["success"] is True
    assert len(result["schemas"]) == 1
    schema = result["schemas"][0]
    assert schema["name"] == "AWS.CloudTrail"
    assert "spec" in schema
    assert "version" in schema
    assert schema["isFieldDiscoveryEnabled"] is True
    mock_client.execute.assert_called_once()


@pytest.mark.asyncio
@patch_graphql_client(SCHEMAS_MODULE_PATH)
async def test_get_log_type_schema_details_multiple_schemas(mock_client):
    """Test retrieval of multiple schema details."""
    # Mock multiple calls for multiple schemas
    mock_client.execute.side_effect = [
        MOCK_SCHEMA_DETAILS_RESPONSE,
        {
            "schemas": {
                "edges": [{"node": {**MOCK_SCHEMA_DETAILED, "name": "GCP.AuditLog"}}]
            }
        },
    ]

    result = await get_log_type_schema_details(["AWS.CloudTrail", "GCP.AuditLog"])

    assert result["success"] is True
    assert len(result["schemas"]) == 2
    assert mock_client.execute.call_count == 2


@pytest.mark.asyncio
async def test_get_log_type_schema_details_no_schema_names():
    """Test handling when no schema names are provided."""
    result = await get_log_type_schema_details([])

    assert result["success"] is False
    assert "No schema names provided" in result["message"]


@pytest.mark.asyncio
async def test_get_log_type_schema_details_too_many_schemas():
    """Test handling when more than 5 schema names are provided."""
    schema_names = [f"Schema{i}" for i in range(6)]

    result = await get_log_type_schema_details(schema_names)

    assert result["success"] is False
    assert "Maximum of 5 schema names allowed" in result["message"]


@pytest.mark.asyncio
@patch_graphql_client(SCHEMAS_MODULE_PATH)
async def test_get_log_type_schema_details_no_matches(mock_client):
    """Test handling when no matching schemas are found."""
    mock_client.execute.return_value = {"schemas": {"edges": []}}

    result = await get_log_type_schema_details(["NonExistentSchema"])

    assert result["success"] is False
    assert "No matching schemas found" in result["message"]


@pytest.mark.asyncio
@patch_graphql_client(SCHEMAS_MODULE_PATH)
async def test_get_log_type_schema_details_exception(mock_client):
    """Test handling of exceptions during schema detail retrieval."""
    mock_client.execute.side_effect = Exception("GraphQL error")

    result = await get_log_type_schema_details(["AWS.CloudTrail"])

    assert result["success"] is False
    assert "Failed to fetch schema details" in result["message"]
    assert "GraphQL error" in result["message"]


@pytest.mark.asyncio
@patch_graphql_client(SCHEMAS_MODULE_PATH)
async def test_get_log_type_schema_details_partial_success(mock_client):
    """Test handling when some schemas are found but others are not."""
    # First call returns data, second call returns empty
    mock_client.execute.side_effect = [
        MOCK_SCHEMA_DETAILS_RESPONSE,
        {"schemas": {"edges": []}},
    ]

    result = await get_log_type_schema_details(["AWS.CloudTrail", "NonExistentSchema"])

    assert result["success"] is True
    assert len(result["schemas"]) == 1
    assert result["schemas"][0]["name"] == "AWS.CloudTrail"
    assert mock_client.execute.call_count == 2
