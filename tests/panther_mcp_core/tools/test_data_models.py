import pytest

from mcp_panther.panther_mcp_core.tools.data_models import (
    get_data_model,
    list_data_models,
)
from tests.utils.helpers import patch_rest_client

MOCK_DATA_MODEL = {
    "id": "StandardDataModel",
    "body": 'def get_event_time(event):\n    return event.get("eventTime")\n\ndef get_user_id(event):\n    return event.get("userId")',
    "description": "Standard data model for user events",
    "displayName": "Standard Data Model",
    "enabled": True,
    "logTypes": ["Custom.UserEvent"],
    "mappings": [
        {"name": "event_time", "path": "eventTime", "method": "get_event_time"},
        {"name": "user_id", "path": "userId", "method": "get_user_id"},
    ],
    "managed": False,
    "createdAt": "2024-11-14T17:09:49.841715953Z",
    "lastModified": "2024-11-14T17:09:49.841716265Z",
}

MOCK_DATA_MODEL_ADVANCED = {
    **MOCK_DATA_MODEL,
    "id": "AdvancedDataModel",
    "displayName": "Advanced Data Model",
    "description": "Advanced data model with complex mappings",
    "logTypes": ["Custom.AdvancedEvent", "Custom.SystemEvent"],
    "mappings": [
        {"name": "timestamp", "path": "ts", "method": "get_timestamp"},
        {"name": "source_ip", "path": "sourceIp", "method": "get_source_ip"},
    ],
}

MOCK_DATA_MODELS_RESPONSE = {
    "results": [MOCK_DATA_MODEL, MOCK_DATA_MODEL_ADVANCED],
    "next": "next-page-token",
}

DATA_MODELS_MODULE_PATH = "mcp_panther.panther_mcp_core.tools.data_models"


@pytest.mark.asyncio
@patch_rest_client(DATA_MODELS_MODULE_PATH)
async def test_list_data_models_success(mock_rest_client):
    """Test successful listing of data models."""
    mock_rest_client.get.return_value = (MOCK_DATA_MODELS_RESPONSE, 200)

    result = await list_data_models()

    assert result["success"] is True
    assert len(result["data_models"]) == 2
    assert result["total_data_models"] == 2
    assert result["has_next_page"] is True
    assert result["next_cursor"] == "next-page-token"

    first_data_model = result["data_models"][0]
    assert first_data_model["id"] == MOCK_DATA_MODEL["id"]
    assert first_data_model["displayName"] == MOCK_DATA_MODEL["displayName"]
    assert first_data_model["enabled"] is True
    assert first_data_model["logTypes"] == MOCK_DATA_MODEL["logTypes"]
    assert first_data_model["mappings"] == MOCK_DATA_MODEL["mappings"]


@pytest.mark.asyncio
@patch_rest_client(DATA_MODELS_MODULE_PATH)
async def test_list_data_models_with_pagination(mock_rest_client):
    """Test listing data models with pagination."""
    mock_rest_client.get.return_value = (MOCK_DATA_MODELS_RESPONSE, 200)

    await list_data_models(cursor="some-cursor", limit=50)

    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    assert args[0] == "/data-models"
    assert kwargs["params"]["cursor"] == "some-cursor"
    assert kwargs["params"]["limit"] == 50


@pytest.mark.asyncio
@patch_rest_client(DATA_MODELS_MODULE_PATH)
async def test_list_data_models_error(mock_rest_client):
    """Test handling of errors when listing data models."""
    mock_rest_client.get.side_effect = Exception("Test error")

    result = await list_data_models()

    assert result["success"] is False
    assert "Failed to list data models" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(DATA_MODELS_MODULE_PATH)
async def test_get_data_model_success(mock_rest_client):
    """Test successful retrieval of a single data model."""
    mock_rest_client.get.return_value = (MOCK_DATA_MODEL, 200)

    result = await get_data_model(MOCK_DATA_MODEL["id"])

    assert result["success"] is True
    assert result["data_model"]["id"] == MOCK_DATA_MODEL["id"]
    assert result["data_model"]["displayName"] == MOCK_DATA_MODEL["displayName"]
    assert result["data_model"]["body"] == MOCK_DATA_MODEL["body"]
    assert len(result["data_model"]["mappings"]) == 2
    assert result["data_model"]["logTypes"] == MOCK_DATA_MODEL["logTypes"]

    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    assert args[0] == f"/data-models/{MOCK_DATA_MODEL['id']}"


@pytest.mark.asyncio
@patch_rest_client(DATA_MODELS_MODULE_PATH)
async def test_get_data_model_not_found(mock_rest_client):
    """Test handling of non-existent data model."""
    mock_rest_client.get.return_value = ({}, 404)

    result = await get_data_model("nonexistent-data-model")

    assert result["success"] is False
    assert "No data model found with ID" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(DATA_MODELS_MODULE_PATH)
async def test_get_data_model_error(mock_rest_client):
    """Test handling of errors when getting data model by ID."""
    mock_rest_client.get.side_effect = Exception("Test error")

    result = await get_data_model(MOCK_DATA_MODEL["id"])

    assert result["success"] is False
    assert "Failed to get data model details" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(DATA_MODELS_MODULE_PATH)
async def test_list_data_models_empty_results(mock_rest_client):
    """Test listing data models with empty results."""
    empty_response = {"results": [], "next": None}
    mock_rest_client.get.return_value = (empty_response, 200)

    result = await list_data_models()

    assert result["success"] is True
    assert len(result["data_models"]) == 0
    assert result["total_data_models"] == 0
    assert result["has_next_page"] is False
    assert result["next_cursor"] is None


@pytest.mark.asyncio
@patch_rest_client(DATA_MODELS_MODULE_PATH)
async def test_list_data_models_with_null_cursor(mock_rest_client):
    """Test listing data models with null cursor."""
    mock_rest_client.get.return_value = (MOCK_DATA_MODELS_RESPONSE, 200)

    await list_data_models(cursor="null")

    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    assert args[0] == "/data-models"
    # Should not include cursor in params when it's "null"
    assert "cursor" not in kwargs["params"]


@pytest.mark.asyncio
@patch_rest_client(DATA_MODELS_MODULE_PATH)
async def test_list_data_models_limit_validation(mock_rest_client):
    """Test listing data models with various limit values."""
    mock_rest_client.get.return_value = (MOCK_DATA_MODELS_RESPONSE, 200)

    # Test with minimum limit
    await list_data_models(limit=1)
    args, kwargs = mock_rest_client.get.call_args
    assert kwargs["params"]["limit"] == 1

    # Test with maximum limit (should be handled by Annotated constraints)
    mock_rest_client.reset_mock()
    await list_data_models(limit=1000)
    args, kwargs = mock_rest_client.get.call_args
    assert kwargs["params"]["limit"] == 1000


@pytest.mark.asyncio
@patch_rest_client(DATA_MODELS_MODULE_PATH)
async def test_get_data_model_with_complex_mappings(mock_rest_client):
    """Test retrieving a data model with complex mappings."""
    complex_data_model = {
        **MOCK_DATA_MODEL_ADVANCED,
        "mappings": [
            {
                "name": "nested_field",
                "path": "data.nested.field",
                "method": "get_nested_field",
            },
            {
                "name": "array_field",
                "path": "items[0].value",
                "method": "get_array_value",
            },
        ],
    }
    mock_rest_client.get.return_value = (complex_data_model, 200)

    result = await get_data_model(complex_data_model["id"])

    assert result["success"] is True
    assert len(result["data_model"]["mappings"]) == 2
    assert result["data_model"]["mappings"][0]["path"] == "data.nested.field"
    assert result["data_model"]["mappings"][1]["path"] == "items[0].value"
