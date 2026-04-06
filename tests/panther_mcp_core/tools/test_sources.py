from unittest.mock import AsyncMock, patch

import pytest

from mcp_panther.panther_mcp_core.tools.sources import (
    create_http_log_source,
    get_http_log_source,
    list_log_sources,
)
from tests.utils.helpers import patch_execute_query, patch_rest_client

SOURCES_MODULE_PATH = "mcp_panther.panther_mcp_core.tools.sources"

MOCK_LOG_SOURCE = {
    "id": "source-123",
    "label": "Test S3 Source",
    "integrationType": "aws-s3",
    "logTypes": ["AWS.CloudTrail", "AWS.S3ServerAccess"],
    "isHealthy": True,
    "bucketName": "test-bucket",
    "createdAt": "2024-01-01T09:00:00Z",
}

MOCK_HTTP_LOG_SOURCE = {
    "integrationId": "http-source-123",
    "integrationLabel": "Test HTTP Source",
    "logTypes": ["Custom.WebhookData"],
    "logStreamType": "JSON",
    "logStreamTypeOptions": {
        "jsonArrayEnvelopeField": None,
    },
    "authMethod": "Bearer",
    "authBearerToken": "test-token-123",
    "authUsername": None,
    "authPassword": None,
    "authHeaderKey": None,
    "authSecretValue": None,
    "authHmacAlg": None,
}

MOCK_SOURCES_QUERY_RESULT = {
    "sources": {
        "edges": [{"node": MOCK_LOG_SOURCE}],
        "pageInfo": {
            "hasNextPage": False,
            "hasPreviousPage": False,
            "endCursor": "cursor-end",
            "startCursor": "cursor-start",
        },
    }
}


def create_mock_graphql_client():
    """Create a mock GraphQL client for testing."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


def create_mock_rest_client():
    """Create a mock REST client for testing."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


@pytest.mark.asyncio
@patch_execute_query(SOURCES_MODULE_PATH)
async def test_list_log_sources_success(mock_execute_query):
    """Test successful listing of log sources."""
    mock_execute_query.return_value = MOCK_SOURCES_QUERY_RESULT

    result = await list_log_sources()

    assert result["success"] is True
    assert len(result["sources"]) == 1
    assert result["sources"][0]["id"] == "source-123"
    assert result["sources"][0]["integrationType"] == "aws-s3"
    assert result["total_sources"] == 1
    assert result["has_next_page"] is False
    assert result["has_previous_page"] is False


@pytest.mark.asyncio
@patch_execute_query(SOURCES_MODULE_PATH)
async def test_list_log_sources_with_filters(mock_execute_query):
    """Test listing log sources with filters applied."""
    mock_execute_query.return_value = MOCK_SOURCES_QUERY_RESULT

    result = await list_log_sources(
        log_types=["AWS.CloudTrail"], is_healthy=True, integration_type="aws-s3"
    )

    assert result["success"] is True
    assert len(result["sources"]) == 1
    # The source should match all filters
    assert result["sources"][0]["isHealthy"] is True
    assert result["sources"][0]["integrationType"] == "aws-s3"
    assert "AWS.CloudTrail" in result["sources"][0]["logTypes"]


@pytest.mark.asyncio
@patch_execute_query(SOURCES_MODULE_PATH)
async def test_list_log_sources_filtering_unhealthy(mock_execute_query):
    """Test filtering out unhealthy sources."""
    mock_unhealthy_source = MOCK_LOG_SOURCE.copy()
    mock_unhealthy_source["isHealthy"] = False
    mock_result = {
        "sources": {
            "edges": [{"node": mock_unhealthy_source}],
            "pageInfo": {
                "hasNextPage": False,
                "hasPreviousPage": False,
                "endCursor": None,
                "startCursor": None,
            },
        }
    }

    mock_execute_query.return_value = mock_result

    # Request only healthy sources (default behavior)
    result = await list_log_sources(is_healthy=True)

    assert result["success"] is True
    assert len(result["sources"]) == 0  # Should be filtered out


@pytest.mark.asyncio
@patch_execute_query(SOURCES_MODULE_PATH)
async def test_list_log_sources_with_pagination(mock_execute_query):
    """Test listing log sources with pagination."""
    mock_execute_query.return_value = MOCK_SOURCES_QUERY_RESULT

    result = await list_log_sources(cursor="test-cursor")

    assert result["success"] is True
    # Verify that cursor was passed in the query variables
    mock_execute_query.assert_called_once()
    call_args = mock_execute_query.call_args
    variables = call_args[0][1]  # Second positional arg is variables dict
    assert variables["input"]["cursor"] == "test-cursor"


@pytest.mark.asyncio
@patch_execute_query(SOURCES_MODULE_PATH)
async def test_list_log_sources_error(mock_execute_query):
    """Test handling of errors when listing log sources."""
    mock_execute_query.side_effect = Exception("GraphQL Error")

    result = await list_log_sources()

    assert result["success"] is False
    assert "Failed to fetch log sources" in result["message"]
    assert "GraphQL Error" in result["message"]


@pytest.mark.asyncio
@patch(f"{SOURCES_MODULE_PATH}.get_rest_client")
async def test_get_http_log_source_success(mock_get_client):
    """Test successful retrieval of an HTTP log source."""
    mock_client = create_mock_rest_client()
    mock_client.get.return_value = (MOCK_HTTP_LOG_SOURCE, 200)
    mock_get_client.return_value = mock_client

    result = await get_http_log_source("http-source-123")

    assert result["success"] is True
    assert result["source"]["integrationId"] == "http-source-123"
    assert result["source"]["integrationLabel"] == "Test HTTP Source"
    assert result["source"]["logStreamType"] == "JSON"
    assert result["source"]["authMethod"] == "Bearer"
    assert result["source"]["authBearerToken"] == "test-token-123"

    mock_client.get.assert_called_once_with("/log-sources/http/http-source-123")


@pytest.mark.asyncio
@patch(f"{SOURCES_MODULE_PATH}.get_rest_client")
async def test_get_http_log_source_with_hmac_auth(mock_get_client):
    """Test retrieval of HTTP log source with HMAC authentication."""
    mock_http_source_hmac = MOCK_HTTP_LOG_SOURCE.copy()
    mock_http_source_hmac.update(
        {
            "authMethod": "HMAC",
            "authBearerToken": None,
            "authHeaderKey": "X-Signature",
            "authSecretValue": "secret-key-123",
            "authHmacAlg": "sha256",
        }
    )

    mock_client = create_mock_rest_client()
    mock_client.get.return_value = (mock_http_source_hmac, 200)
    mock_get_client.return_value = mock_client

    result = await get_http_log_source("http-source-hmac")

    assert result["success"] is True
    assert result["source"]["authMethod"] == "HMAC"
    assert result["source"]["authHeaderKey"] == "X-Signature"
    assert result["source"]["authSecretValue"] == "secret-key-123"
    assert result["source"]["authHmacAlg"] == "sha256"
    assert result["source"]["authBearerToken"] is None


@pytest.mark.asyncio
@patch(f"{SOURCES_MODULE_PATH}.get_rest_client")
async def test_get_http_log_source_with_basic_auth(mock_get_client):
    """Test retrieval of HTTP log source with Basic authentication."""
    mock_http_source_basic = MOCK_HTTP_LOG_SOURCE.copy()
    mock_http_source_basic.update(
        {
            "authMethod": "Basic",
            "authBearerToken": None,
            "authUsername": "testuser",
            "authPassword": "testpass",
            "authHeaderKey": None,
            "authSecretValue": None,
            "authHmacAlg": None,
        }
    )

    mock_client = create_mock_rest_client()
    mock_client.get.return_value = (mock_http_source_basic, 200)
    mock_get_client.return_value = mock_client

    result = await get_http_log_source("http-source-basic")

    assert result["success"] is True
    assert result["source"]["authMethod"] == "Basic"
    assert result["source"]["authUsername"] == "testuser"
    assert result["source"]["authPassword"] == "testpass"


@pytest.mark.asyncio
@patch(f"{SOURCES_MODULE_PATH}.get_rest_client")
async def test_get_http_log_source_not_found(mock_get_client):
    """Test handling of HTTP log source not found."""
    mock_client = create_mock_rest_client()
    mock_client.get.side_effect = Exception("HTTP 404: Not Found")
    mock_get_client.return_value = mock_client

    result = await get_http_log_source("nonexistent-source")

    assert result["success"] is False
    assert "Failed to fetch HTTP log source" in result["message"]
    assert "HTTP 404: Not Found" in result["message"]


@pytest.mark.asyncio
@patch(f"{SOURCES_MODULE_PATH}.get_rest_client")
async def test_get_http_log_source_error(mock_get_client):
    """Test handling of general errors when getting HTTP log source."""
    mock_client = create_mock_rest_client()
    mock_client.get.side_effect = Exception("Connection error")
    mock_get_client.return_value = mock_client

    result = await get_http_log_source("http-source-123")

    assert result["success"] is False
    assert "Failed to fetch HTTP log source" in result["message"]
    assert "Connection error" in result["message"]


@pytest.mark.asyncio
@patch(f"{SOURCES_MODULE_PATH}.get_rest_client")
async def test_get_http_log_source_with_json_array_stream_type(mock_get_client):
    """Test HTTP log source with JsonArray stream type and envelope field."""
    mock_http_source_json_array = MOCK_HTTP_LOG_SOURCE.copy()
    mock_http_source_json_array.update(
        {
            "logStreamType": "JsonArray",
            "logStreamTypeOptions": {
                "jsonArrayEnvelopeField": "events",
            },
        }
    )

    mock_client = create_mock_rest_client()
    mock_client.get.return_value = (mock_http_source_json_array, 200)
    mock_get_client.return_value = mock_client

    result = await get_http_log_source("http-source-json-array")

    assert result["success"] is True
    assert result["source"]["logStreamType"] == "JsonArray"
    assert (
        result["source"]["logStreamTypeOptions"]["jsonArrayEnvelopeField"] == "events"
    )


# =====================================================================
# create_http_log_source tests
# =====================================================================

MOCK_CREATED_HTTP_SOURCE = {
    "integrationId": "new-http-source-123",
    "integrationLabel": "My Webhook Source",
    "logTypes": ["Custom.WebhookData"],
    "logStreamType": "JSON",
    "logStreamTypeOptions": None,
    "authMethod": "None",
    "authBearerToken": None,
    "authUsername": None,
    "authPassword": None,
    "authHeaderKey": None,
    "authSecretValue": None,
    "authHmacAlg": None,
}


@pytest.mark.asyncio
@patch_rest_client(SOURCES_MODULE_PATH)
async def test_create_http_log_source_no_auth(mock_client):
    """Test creating an HTTP log source with no authentication."""
    mock_client.post.return_value = (MOCK_CREATED_HTTP_SOURCE, 201)

    result = await create_http_log_source(
        integration_label="My Webhook Source",
        log_types=["Custom.WebhookData"],
        log_stream_type="JSON",
        auth_method="None",
    )

    assert result["success"] is True
    assert result["source"]["integrationId"] == "new-http-source-123"
    assert result["source"]["integrationLabel"] == "My Webhook Source"
    assert result["source"]["authMethod"] == "None"

    mock_client.post.assert_called_once_with(
        "/log-sources/http",
        json_data={
            "integrationLabel": "My Webhook Source",
            "logTypes": ["Custom.WebhookData"],
            "logStreamType": "JSON",
            "authMethod": "None",
        },
        expected_codes=[201],
    )


@pytest.mark.asyncio
@patch_rest_client(SOURCES_MODULE_PATH)
async def test_create_http_log_source_bearer_auth(mock_client):
    """Test creating an HTTP log source with Bearer authentication."""
    mock_response = MOCK_CREATED_HTTP_SOURCE.copy()
    mock_response.update(
        {
            "authMethod": "Bearer",
            "authBearerToken": "my-secret-token",
        }
    )
    mock_client.post.return_value = (mock_response, 201)

    result = await create_http_log_source(
        integration_label="My Webhook Source",
        log_types=["Custom.WebhookData"],
        log_stream_type="JSON",
        auth_method="Bearer",
        auth_bearer_token="my-secret-token",
    )

    assert result["success"] is True
    assert result["source"]["authMethod"] == "Bearer"
    assert result["source"]["authBearerToken"] == "my-secret-token"

    call_args = mock_client.post.call_args
    assert call_args[1]["json_data"]["authBearerToken"] == "my-secret-token"


@pytest.mark.asyncio
@patch_rest_client(SOURCES_MODULE_PATH)
async def test_create_http_log_source_basic_auth(mock_client):
    """Test creating an HTTP log source with Basic authentication."""
    mock_response = MOCK_CREATED_HTTP_SOURCE.copy()
    mock_response.update(
        {
            "authMethod": "Basic",
            "authUsername": "testuser",
            "authPassword": "testpass",
        }
    )
    mock_client.post.return_value = (mock_response, 201)

    result = await create_http_log_source(
        integration_label="My Webhook Source",
        log_types=["Custom.WebhookData"],
        log_stream_type="JSON",
        auth_method="Basic",
        auth_username="testuser",
        auth_password="testpass",
    )

    assert result["success"] is True
    assert result["source"]["authMethod"] == "Basic"

    call_args = mock_client.post.call_args
    assert call_args[1]["json_data"]["authUsername"] == "testuser"
    assert call_args[1]["json_data"]["authPassword"] == "testpass"


@pytest.mark.asyncio
@patch_rest_client(SOURCES_MODULE_PATH)
async def test_create_http_log_source_hmac_auth(mock_client):
    """Test creating an HTTP log source with HMAC authentication."""
    mock_response = MOCK_CREATED_HTTP_SOURCE.copy()
    mock_response.update(
        {
            "authMethod": "HMAC",
            "authHeaderKey": "X-Signature",
            "authSecretValue": "secret-key",
            "authHmacAlg": "sha256",
        }
    )
    mock_client.post.return_value = (mock_response, 201)

    result = await create_http_log_source(
        integration_label="My Webhook Source",
        log_types=["Custom.WebhookData"],
        log_stream_type="JSON",
        auth_method="HMAC",
        auth_header_key="X-Signature",
        auth_secret_value="secret-key",
        auth_hmac_alg="sha256",
    )

    assert result["success"] is True
    assert result["source"]["authMethod"] == "HMAC"

    call_args = mock_client.post.call_args
    assert call_args[1]["json_data"]["authHeaderKey"] == "X-Signature"
    assert call_args[1]["json_data"]["authSecretValue"] == "secret-key"
    assert call_args[1]["json_data"]["authHmacAlg"] == "sha256"


@pytest.mark.asyncio
@patch_rest_client(SOURCES_MODULE_PATH)
async def test_create_http_log_source_shared_secret_auth(mock_client):
    """Test creating an HTTP log source with SharedSecret authentication."""
    mock_response = MOCK_CREATED_HTTP_SOURCE.copy()
    mock_response.update(
        {
            "authMethod": "SharedSecret",
            "authHeaderKey": "X-Secret",
            "authSecretValue": "my-secret",
        }
    )
    mock_client.post.return_value = (mock_response, 201)

    result = await create_http_log_source(
        integration_label="My Webhook Source",
        log_types=["Custom.WebhookData"],
        log_stream_type="JSON",
        auth_method="SharedSecret",
        auth_header_key="X-Secret",
        auth_secret_value="my-secret",
    )

    assert result["success"] is True
    assert result["source"]["authMethod"] == "SharedSecret"

    call_args = mock_client.post.call_args
    assert call_args[1]["json_data"]["authHeaderKey"] == "X-Secret"
    assert call_args[1]["json_data"]["authSecretValue"] == "my-secret"


@pytest.mark.asyncio
@patch_rest_client(SOURCES_MODULE_PATH)
async def test_create_http_log_source_with_json_array_envelope(mock_client):
    """Test creating an HTTP log source with JsonArray stream type and envelope field."""
    mock_response = MOCK_CREATED_HTTP_SOURCE.copy()
    mock_response.update(
        {
            "logStreamType": "JsonArray",
            "logStreamTypeOptions": {"jsonArrayEnvelopeField": "events"},
        }
    )
    mock_client.post.return_value = (mock_response, 201)

    result = await create_http_log_source(
        integration_label="My Webhook Source",
        log_types=["Custom.WebhookData"],
        log_stream_type="JsonArray",
        auth_method="None",
        json_array_envelope_field="events",
    )

    assert result["success"] is True
    assert result["source"]["logStreamType"] == "JsonArray"

    call_args = mock_client.post.call_args
    assert call_args[1]["json_data"]["logStreamTypeOptions"] == {
        "jsonArrayEnvelopeField": "events"
    }


@pytest.mark.asyncio
async def test_create_http_log_source_missing_bearer_token():
    """Test that missing bearer token returns validation error."""
    result = await create_http_log_source(
        integration_label="My Webhook Source",
        log_types=["Custom.WebhookData"],
        log_stream_type="JSON",
        auth_method="Bearer",
    )

    assert result["success"] is False
    assert "auth_bearer_token is required" in result["message"]


@pytest.mark.asyncio
async def test_create_http_log_source_missing_basic_auth_fields():
    """Test that missing basic auth fields return validation error."""
    result = await create_http_log_source(
        integration_label="My Webhook Source",
        log_types=["Custom.WebhookData"],
        log_stream_type="JSON",
        auth_method="Basic",
    )

    assert result["success"] is False
    assert "auth_username and auth_password are required" in result["message"]


@pytest.mark.asyncio
async def test_create_http_log_source_missing_hmac_fields():
    """Test that missing HMAC fields return validation error."""
    result = await create_http_log_source(
        integration_label="My Webhook Source",
        log_types=["Custom.WebhookData"],
        log_stream_type="JSON",
        auth_method="HMAC",
        auth_header_key="X-Signature",
    )

    assert result["success"] is False
    assert (
        "auth_header_key, auth_secret_value, and auth_hmac_alg are required"
        in result["message"]
    )


@pytest.mark.asyncio
async def test_create_http_log_source_missing_shared_secret_fields():
    """Test that missing SharedSecret fields return validation error."""
    result = await create_http_log_source(
        integration_label="My Webhook Source",
        log_types=["Custom.WebhookData"],
        log_stream_type="JSON",
        auth_method="SharedSecret",
    )

    assert result["success"] is False
    assert "auth_header_key and auth_secret_value are required" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(SOURCES_MODULE_PATH)
async def test_create_http_log_source_api_error(mock_client):
    """Test handling of API errors during creation."""
    mock_client.post.side_effect = Exception(
        'Request failed (HTTP 400): {"message": "invalid log type"}'
    )

    result = await create_http_log_source(
        integration_label="My Webhook Source",
        log_types=["Invalid.LogType"],
        log_stream_type="JSON",
        auth_method="None",
    )

    assert result["success"] is False
    assert "Failed to create HTTP log source" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(SOURCES_MODULE_PATH)
async def test_create_http_log_source_conflict_error(mock_client):
    """Test handling of conflict (duplicate) errors during creation."""
    mock_client.post.side_effect = Exception(
        'Request failed (HTTP 409): {"message": "source already exists"}'
    )

    result = await create_http_log_source(
        integration_label="Duplicate Source",
        log_types=["Custom.WebhookData"],
        log_stream_type="JSON",
        auth_method="None",
    )

    assert result["success"] is False
    assert "Failed to create HTTP log source" in result["message"]
    assert "409" in result["message"]
