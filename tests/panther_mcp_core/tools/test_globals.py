import pytest

from mcp_panther.panther_mcp_core.tools.global_helpers import (
    get_global_helper,
    list_global_helpers,
)
from tests.utils.helpers import patch_rest_client

MOCK_GLOBAL = {
    "id": "MyGlobalHelper",
    "body": 'def is_suspicious_ip(ip_address):\n    """Check if an IP address is suspicious based on reputation data."""\n    suspicious_ranges = ["192.168.1.0/24", "10.0.0.0/8"]\n    return any(ip_address.startswith(range_prefix.split("/")[0]) for range_prefix in suspicious_ranges)',
    "description": "Helper function to check if an IP address is suspicious",
    "tags": ["security", "ip-validation"],
    "createdAt": "2024-11-14T17:09:49.841715953Z",
    "lastModified": "2024-11-14T17:09:49.841716265Z",
}

MOCK_GLOBAL_ADVANCED = {
    **MOCK_GLOBAL,
    "id": "AdvancedParser",
    "displayName": "Advanced Log Parser",
    "description": "Advanced parsing utilities for complex log formats",
    "body": 'def parse_complex_log(log_entry):\n    """Parse complex log entries and extract key fields."""\n    import json\n    try:\n        return json.loads(log_entry)\n    except:\n        return {}',
}

MOCK_GLOBALS_RESPONSE = {
    "results": [MOCK_GLOBAL, MOCK_GLOBAL_ADVANCED],
    "next": "next-page-token",
}

GLOBALS_MODULE_PATH = "mcp_panther.panther_mcp_core.tools.global_helpers"


@pytest.mark.asyncio
@patch_rest_client(GLOBALS_MODULE_PATH)
async def test_list_globals_success(mock_rest_client):
    """Test successful listing of global helpers."""
    mock_rest_client.get.return_value = (MOCK_GLOBALS_RESPONSE, 200)

    result = await list_global_helpers()

    assert result["success"] is True
    assert len(result["global_helpers"]) == 2
    assert result["total_global_helpers"] == 2
    assert result["has_next_page"] is True
    assert result["next_cursor"] == "next-page-token"

    first_global = result["global_helpers"][0]
    assert first_global["id"] == MOCK_GLOBAL["id"]
    assert first_global["description"] == MOCK_GLOBAL["description"]
    assert first_global["tags"] == MOCK_GLOBAL.get("tags")
    assert first_global["createdAt"] == MOCK_GLOBAL["createdAt"]
    assert first_global["lastModified"] == MOCK_GLOBAL["lastModified"]


@pytest.mark.asyncio
@patch_rest_client(GLOBALS_MODULE_PATH)
async def test_list_globals_with_pagination(mock_rest_client):
    """Test listing global helpers with pagination."""
    mock_rest_client.get.return_value = (MOCK_GLOBALS_RESPONSE, 200)

    await list_global_helpers(cursor="some-cursor", limit=50)

    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    assert args[0] == "/globals"
    assert kwargs["params"]["cursor"] == "some-cursor"
    assert kwargs["params"]["limit"] == 50


@pytest.mark.asyncio
@patch_rest_client(GLOBALS_MODULE_PATH)
async def test_list_globals_with_filters(mock_rest_client):
    """Test listing global helpers with various filters."""
    mock_rest_client.get.return_value = (MOCK_GLOBALS_RESPONSE, 200)

    await list_global_helpers(
        name_contains="Helper", created_by="user-123", last_modified_by="user-456"
    )

    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    assert args[0] == "/globals"
    assert kwargs["params"]["name-contains"] == "Helper"
    assert kwargs["params"]["created-by"] == "user-123"
    assert kwargs["params"]["last-modified-by"] == "user-456"


@pytest.mark.asyncio
@patch_rest_client(GLOBALS_MODULE_PATH)
async def test_list_globals_error(mock_rest_client):
    """Test handling of errors when listing global helpers."""
    mock_rest_client.get.side_effect = Exception("Test error")

    result = await list_global_helpers()

    assert result["success"] is False
    assert "Failed to list global helpers" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(GLOBALS_MODULE_PATH)
async def test_get_global_success(mock_rest_client):
    """Test successful retrieval of a single global helper."""
    mock_rest_client.get.return_value = (MOCK_GLOBAL, 200)

    result = await get_global_helper(MOCK_GLOBAL["id"])

    assert result["success"] is True
    assert result["global_helper"]["id"] == MOCK_GLOBAL["id"]
    assert result["global_helper"]["description"] == MOCK_GLOBAL["description"]
    assert result["global_helper"]["body"] == MOCK_GLOBAL["body"]
    assert result["global_helper"]["tags"] == MOCK_GLOBAL["tags"]

    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    assert args[0] == f"/globals/{MOCK_GLOBAL['id']}"


@pytest.mark.asyncio
@patch_rest_client(GLOBALS_MODULE_PATH)
async def test_get_global_not_found(mock_rest_client):
    """Test handling of non-existent global helper."""
    mock_rest_client.get.return_value = ({}, 404)

    result = await get_global_helper("nonexistent-global")

    assert result["success"] is False
    assert "No global helper found with ID" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(GLOBALS_MODULE_PATH)
async def test_get_global_error(mock_rest_client):
    """Test handling of errors when getting global helper by ID."""
    mock_rest_client.get.side_effect = Exception("Test error")

    result = await get_global_helper(MOCK_GLOBAL["id"])

    assert result["success"] is False
    assert "Failed to get global helper details" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(GLOBALS_MODULE_PATH)
async def test_list_globals_empty_results(mock_rest_client):
    """Test listing global helpers with empty results."""
    empty_response = {"results": [], "next": None}
    mock_rest_client.get.return_value = (empty_response, 200)

    result = await list_global_helpers()

    assert result["success"] is True
    assert len(result["global_helpers"]) == 0
    assert result["total_global_helpers"] == 0
    assert result["has_next_page"] is False
    assert result["next_cursor"] is None


@pytest.mark.asyncio
@patch_rest_client(GLOBALS_MODULE_PATH)
async def test_list_globals_with_null_cursor(mock_rest_client):
    """Test listing global helpers with null cursor."""
    mock_rest_client.get.return_value = (MOCK_GLOBALS_RESPONSE, 200)

    await list_global_helpers(cursor="null")

    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    assert args[0] == "/globals"
    # Should not include cursor in params when it's "null"
    assert "cursor" not in kwargs["params"]


@pytest.mark.asyncio
@patch_rest_client(GLOBALS_MODULE_PATH)
async def test_list_globals_limit_validation(mock_rest_client):
    """Test listing global helpers with various limit values."""
    mock_rest_client.get.return_value = (MOCK_GLOBALS_RESPONSE, 200)

    # Test with minimum limit
    await list_global_helpers(limit=1)
    args, kwargs = mock_rest_client.get.call_args
    assert kwargs["params"]["limit"] == 1

    # Test with maximum limit (should be handled by Annotated constraints)
    mock_rest_client.reset_mock()
    await list_global_helpers(limit=1000)
    args, kwargs = mock_rest_client.get.call_args
    assert kwargs["params"]["limit"] == 1000


@pytest.mark.asyncio
@patch_rest_client(GLOBALS_MODULE_PATH)
async def test_get_global_with_complex_body(mock_rest_client):
    """Test retrieving a global helper with complex Python code."""
    complex_global = {
        **MOCK_GLOBAL_ADVANCED,
        "body": 'def advanced_threat_detection(event):\n    """Advanced threat detection logic."""\n    import re\n    patterns = [\n        r"malware\\.exe",\n        r"suspicious_activity",\n        r"unauthorized_access"\n    ]\n    return any(re.search(pattern, str(event)) for pattern in patterns)',
    }
    mock_rest_client.get.return_value = (complex_global, 200)

    result = await get_global_helper(complex_global["id"])

    assert result["success"] is True
    assert "advanced_threat_detection" in result["global_helper"]["body"]
    assert "import re" in result["global_helper"]["body"]
    assert len(result["global_helper"]["body"].split("\n")) > 5  # Multi-line function
