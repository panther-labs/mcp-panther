import pytest

from mcp_panther.panther_mcp_core.tools.roles import (
    get_role,
    list_roles,
)
from tests.utils.helpers import patch_rest_client

MOCK_ROLE = {
    "id": "Admin",
    "name": "Administrator",
    "description": "Full administrative access to Panther",
    "permissions": [
        "RULE_READ",
        "RULE_WRITE",
        "USER_READ",
        "USER_WRITE",
        "DATA_ANALYTICS_READ",
    ],
    "managed": True,
    "createdAt": "2024-11-14T17:09:49.841715953Z",
    "lastModified": "2024-11-14T17:09:49.841716265Z",
}

MOCK_ROLE_ANALYST = {
    **MOCK_ROLE,
    "id": "Analyst",
    "name": "Security Analyst",
    "description": "Read-only access for security analysts",
    "permissions": ["RULE_READ", "DATA_ANALYTICS_READ"],
    "managed": False,
}

MOCK_ROLES_RESPONSE = {
    "results": [MOCK_ROLE, MOCK_ROLE_ANALYST],
    "next": "next-page-token",
}

ROLES_MODULE_PATH = "mcp_panther.panther_mcp_core.tools.roles"


@pytest.mark.asyncio
@patch_rest_client(ROLES_MODULE_PATH)
async def test_list_roles_success(mock_rest_client):
    """Test successful listing of roles."""
    mock_rest_client.get.return_value = (MOCK_ROLES_RESPONSE, 200)

    result = await list_roles()

    assert result["success"] is True
    assert len(result["roles"]) == 2
    assert result["total_roles"] == 2
    assert result["has_next_page"] is True
    assert result["next_cursor"] == "next-page-token"

    first_role = result["roles"][0]
    assert first_role["id"] == MOCK_ROLE["id"]
    assert first_role["name"] == MOCK_ROLE["name"]
    assert first_role["permissions"] == MOCK_ROLE["permissions"]
    assert first_role["createdAt"] == MOCK_ROLE["createdAt"]
    # Note: API returns updatedAt, not lastModified for roles


@pytest.mark.asyncio
@patch_rest_client(ROLES_MODULE_PATH)
async def test_list_roles_with_filters(mock_rest_client):
    """Test listing roles with various filters."""
    mock_rest_client.get.return_value = (MOCK_ROLES_RESPONSE, 200)

    await list_roles(
        name_contains="Admin", role_ids=["Admin", "Analyst"], sort_dir="desc"
    )

    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    assert args[0] == "/roles"
    assert kwargs["params"]["name-contains"] == "Admin"
    assert kwargs["params"]["ids"] == "Admin,Analyst"
    assert kwargs["params"]["sort-dir"] == "desc"


@pytest.mark.asyncio
@patch_rest_client(ROLES_MODULE_PATH)
async def test_list_roles_error(mock_rest_client):
    """Test handling of errors when listing roles."""
    mock_rest_client.get.side_effect = Exception("Test error")

    result = await list_roles()

    assert result["success"] is False
    assert "Failed to list roles" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(ROLES_MODULE_PATH)
async def test_get_role_success(mock_rest_client):
    """Test successful retrieval of a single role."""
    mock_rest_client.get.return_value = (MOCK_ROLE, 200)

    result = await get_role(MOCK_ROLE["id"])

    assert result["success"] is True
    assert result["role"]["id"] == MOCK_ROLE["id"]
    assert result["role"]["name"] == MOCK_ROLE["name"]
    assert result["role"]["description"] == MOCK_ROLE["description"]
    assert result["role"]["permissions"] == MOCK_ROLE["permissions"]
    assert result["role"]["managed"] is True

    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    assert args[0] == f"/roles/{MOCK_ROLE['id']}"


@pytest.mark.asyncio
@patch_rest_client(ROLES_MODULE_PATH)
async def test_get_role_not_found(mock_rest_client):
    """Test handling of non-existent role."""
    mock_rest_client.get.return_value = ({}, 404)

    result = await get_role("nonexistent-role")

    assert result["success"] is False
    assert "No role found with ID" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(ROLES_MODULE_PATH)
async def test_get_role_error(mock_rest_client):
    """Test handling of errors when getting role by ID."""
    mock_rest_client.get.side_effect = Exception("Test error")

    result = await get_role(MOCK_ROLE["id"])

    assert result["success"] is False
    assert "Failed to get role details" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(ROLES_MODULE_PATH)
async def test_list_roles_empty_results(mock_rest_client):
    """Test listing roles with empty results."""
    empty_response = {"results": [], "next": None}
    mock_rest_client.get.return_value = (empty_response, 200)

    result = await list_roles()

    assert result["success"] is True
    assert len(result["roles"]) == 0
    assert result["total_roles"] == 0
    assert result["has_next_page"] is False
    assert result["next_cursor"] is None


@pytest.mark.asyncio
@patch_rest_client(ROLES_MODULE_PATH)
async def test_list_roles_with_name_exact_match(mock_rest_client):
    """Test listing roles with exact name match."""
    mock_rest_client.get.return_value = (MOCK_ROLES_RESPONSE, 200)

    await list_roles(name="Admin")

    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    assert args[0] == "/roles"
    assert kwargs["params"]["name"] == "Admin"


@pytest.mark.asyncio
@patch_rest_client(ROLES_MODULE_PATH)
async def test_list_roles_default_sort_direction(mock_rest_client):
    """Test listing roles with default sort direction."""
    mock_rest_client.get.return_value = (MOCK_ROLES_RESPONSE, 200)

    await list_roles()

    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    assert args[0] == "/roles"
    assert kwargs["params"]["sort-dir"] == "asc"
