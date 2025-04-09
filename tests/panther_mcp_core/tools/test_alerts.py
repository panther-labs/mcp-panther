import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from mcp_panther.panther_mcp_core.tools.alerts import (
    list_alerts,
    get_alert_by_id,
    update_alert_status,
    add_alert_comment,
    update_alert_assignee_by_id,
)

MOCK_ALERT = {
    "id": "alert-123",
    "title": "Test Alert",
    "severity": "HIGH",
    "status": "OPEN",
    "createdAt": "2024-03-20T00:00:00Z",
    "updatedAt": "2024-03-20T00:00:00Z",
}

MOCK_ALERTS_RESPONSE = {
    "alerts": {
        "edges": [
            {"node": MOCK_ALERT},
            {"node": {**MOCK_ALERT, "id": "alert-456"}},
        ],
        "pageInfo": {
            "hasNextPage": False,
            "hasPreviousPage": False,
            "endCursor": "cursor123",
            "startCursor": "cursor123",
        },
    }
}

@pytest.fixture
def mock_graphql_client():
    """Fixture to create a mock GraphQL client."""
    with patch("mcp_panther.panther_mcp_core.tools.alerts._create_panther_client") as mock_create:
        session = AsyncMock()
        execute_mock = AsyncMock()
        
        # Set up the execute mock to return the value we want
        async def side_effect(*args, **kwargs):
            return session.execute_return_value
            
        execute_mock.side_effect = side_effect
        session.execute = execute_mock
        
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        
        mock_create.return_value = session
        yield session

@pytest.fixture
def mock_execute_query():
    """Fixture to create a mock for the _execute_query function."""
    with patch("mcp_panther.panther_mcp_core.tools.alerts._execute_query") as mock:
        # Create an async mock that can be customized for each test
        async_mock = AsyncMock()
        mock.side_effect = async_mock
        yield async_mock

@pytest.mark.asyncio
async def test_list_alerts_success(mock_graphql_client):
    """Test successful listing of alerts."""
    # Set the return value for execute
    mock_graphql_client.execute_return_value = MOCK_ALERTS_RESPONSE
    
    result = await list_alerts()
    print(result)
    assert result["success"] is True
    assert len(result["alerts"]) == 2
    assert result["total_alerts"] == 2
    assert result["has_next_page"] is False
    assert result["end_cursor"] == "cursor123"

    # Verify the first alert
    first_alert = result["alerts"][0]
    assert first_alert["id"] == "alert-123"
    assert first_alert["severity"] == "HIGH"
    assert first_alert["status"] == "OPEN"

@pytest.mark.asyncio
async def test_list_alerts_with_invalid_page_size(mock_graphql_client):
    """Test handling of invalid page size."""
    mock_graphql_client.execute_return_value = MOCK_ALERTS_RESPONSE

    # Test with page size < 1
    result = await list_alerts(page_size=0)
    assert result["success"] is False
    assert "page_size must be greater than 0" in result["message"]

    # Test with page size > 50
    await list_alerts(page_size=100)
    mock_graphql_client.execute.assert_called_once()
    call_args = mock_graphql_client.execute.call_args[1]["variable_values"]
    assert call_args["input"]["pageSize"] == 50

@pytest.mark.asyncio
async def test_list_alerts_with_filters(mock_graphql_client):
    """Test listing alerts with various filters."""
    mock_graphql_client.execute_return_value = MOCK_ALERTS_RESPONSE

    start_date = "2024-03-01T00:00:00Z"
    end_date = "2024-03-31T23:59:59Z"

    result = await list_alerts(
        cursor="next-page-plz",
        severities=["HIGH"],
        statuses=["OPEN"],
        start_date=start_date,
        end_date=end_date,
        event_count_min=1,
        event_count_max=1337,
        log_sources=["my-load-balancer"],
        log_types=["AWS.ALB"],
        page_size=25,
        resource_types=["my-resource-type"],
        subtypes=["RULE"],
        name_contains="Test",
    )

    assert result["success"] is True
  
    # Verify that mock was called with correct filters
    call_args = mock_graphql_client.execute.call_args[1]["variable_values"]
    assert call_args["input"]["cursor"] == "next-page-plz"
    assert call_args["input"]["severities"] == ["HIGH"]
    assert call_args["input"]["statuses"] == ["OPEN"]
    assert call_args["input"]["createdAtAfter"] == start_date
    assert call_args["input"]["createdAtBefore"] == end_date 
    assert call_args["input"]["eventCountMin"] == 1
    assert call_args["input"]["eventCountMax"] == 1337
    assert call_args["input"]["logSources"] == ["my-load-balancer"]
    assert call_args["input"]["logTypes"] == ["AWS.ALB"]
    assert call_args["input"]["pageSize"] == 25
    assert call_args["input"]["resourceTypes"] == ["my-resource-type"]
    assert call_args["input"]["subtypes"] == ["RULE"]
    assert call_args["input"]["nameContains"] == "Test"

@pytest.mark.asyncio
async def test_list_alerts_with_detection_id(mock_graphql_client):
    """Test listing alerts with detection ID."""
    mock_graphql_client.execute_return_value = MOCK_ALERTS_RESPONSE

    result = await list_alerts(detection_id="detection-123")

    assert result["success"] is True
    call_args = mock_graphql_client.execute.call_args[1]["variable_values"]
    assert call_args["input"]["detectionId"] == "detection-123"

    # When detection_id is provided, date range should not be set
    assert "createdAtAfter" not in call_args["input"]
    assert "createdAtBefore" not in call_args["input"]

@pytest.mark.asyncio
async def test_list_alerts_with_invalid_alert_type(mock_graphql_client):
    """Test handling of invalid alert type."""
    result = await list_alerts(alert_type="INVALID")
    assert result["success"] is False
    assert "alert_type must be one of" in result["message"]

@pytest.mark.asyncio
async def test_list_alerts_with_invalid_subtypes(mock_graphql_client):
    """Test handling of invalid subtypes."""
    # Test invalid subtype for ALERT type
    result = await list_alerts(
        alert_type="ALERT",
        subtypes=["INVALID_SUBTYPE"]
    )
    assert result["success"] is False
    assert "Invalid subtypes" in result["message"]

    # Test subtypes with SYSTEM_ERROR type
    result = await list_alerts(
        alert_type="SYSTEM_ERROR",
        subtypes=["ANY_SUBTYPE"]
    )
    assert result["success"] is False
    assert "subtypes are not allowed" in result["message"]

@pytest.mark.asyncio
async def test_list_alerts_error(mock_graphql_client):
    """Test handling of errors when listing alerts."""
    mock_graphql_client.execute.side_effect = Exception("Test error")

    result = await list_alerts()

    assert result["success"] is False
    assert "Failed to fetch alerts" in result["message"]

@pytest.mark.asyncio
async def test_get_alert_by_id_success(mock_graphql_client):
    """Test successful retrieval of a single alert."""
    mock_graphql_client.execute_return_value = {"alert": MOCK_ALERT}

    result = await get_alert_by_id("alert-123")

    assert result["success"] is True
    assert result["alert"]["id"] == "alert-123"
    assert result["alert"]["severity"] == "HIGH"
    assert result["alert"]["status"] == "OPEN"

@pytest.mark.asyncio
async def test_get_alert_by_id_not_found(mock_graphql_client):
    """Test handling of non-existent alert."""
    mock_graphql_client.execute_return_value = {"alert": None}

    result = await get_alert_by_id("nonexistent-alert")

    assert result["success"] is False
    assert "No alert found" in result["message"]

@pytest.mark.asyncio
async def test_get_alert_by_id_error(mock_graphql_client):
    """Test handling of errors when getting alert by ID."""
    mock_graphql_client.execute.side_effect = Exception("Test error")

    result = await get_alert_by_id("alert-123")

    assert result["success"] is False
    assert "Failed to fetch alert details" in result["message"]

@pytest.mark.asyncio
async def test_update_alert_status_success(mock_execute_query):
    """Test successful update of alert status."""
    mock_response = {
        "updateAlertStatusById": {
            "alerts": [
                {**MOCK_ALERT, "status": "TRIAGED"}
            ]
        }
    }

    mock_execute_query.return_value = mock_response
    
    result = await update_alert_status(["alert-123"], "TRIAGED")

    assert result["success"] is True
    assert result["alerts"][0]["status"] == "TRIAGED"
    
    # Verify _execute_query was called with correct parameters
    mock_execute_query.assert_called_once()
    call_args = mock_execute_query.call_args
    assert call_args[0][1]["input"]["ids"] == ["alert-123"]
    assert call_args[0][1]["input"]["status"] == "TRIAGED"

@pytest.mark.asyncio
async def test_update_alert_status_invalid_status():
    """Test handling of invalid status value."""
    result = await update_alert_status(["alert-123"], "INVALID_STATUS")

    assert result["success"] is False
    assert "Status must be one of" in result["message"]

@pytest.mark.asyncio
async def test_update_alert_status_error(mock_execute_query):
    """Test handling of errors when updating alert status."""
    mock_execute_query.side_effect = Exception("Test error")

    result = await update_alert_status(["alert-123"], "TRIAGED")

    assert result["success"] is False
    assert "Failed to update alert status" in result["message"]

@pytest.mark.asyncio
async def test_update_alert_status_with_empty_result(mock_execute_query):
    """Test updating alert status with empty result."""
    mock_response = {}  # no updateAlertStatusById in result
    mock_execute_query.return_value = mock_response

    result = await update_alert_status(["alert-123"], "TRIAGED")

    assert result["success"] is False
    assert "Failed to update alert status" in result["message"]

@pytest.mark.asyncio
async def test_add_alert_comment_success(mock_execute_query):
    """Test successful addition of a comment to an alert."""
    mock_comment = {
        "id": "comment-123",
        "body": "Test comment",
        "createdAt": "2024-03-20T00:00:00Z",
    }
    mock_response = {
        "createAlertComment": {"comment": mock_comment}
    }
    
    mock_execute_query.return_value = mock_response

    result = await add_alert_comment("alert-123", "Test comment")

    assert result["success"] is True
    assert result["comment"]["body"] == "Test comment"

@pytest.mark.asyncio
async def test_add_alert_comment_error(mock_execute_query):
    """Test handling of errors when adding a comment."""
    mock_execute_query.side_effect = Exception("Test error")

    result = await add_alert_comment("alert-123", "Test comment")

    assert result["success"] is False
    assert "Failed to add alert comment" in result["message"]

@pytest.mark.asyncio
async def test_add_alert_comment_with_empty_result(mock_execute_query):
    """Test adding alert comment with empty result."""
    mock_response = {}  # no createAlertComment in result
    mock_execute_query.return_value = mock_response

    result = await add_alert_comment("alert-123", "Test comment")

    assert result["success"] is False
    assert "Failed to add alert comment" in result["message"]

@pytest.mark.asyncio
async def test_update_alert_assignee_success(mock_execute_query):
    """Test successful update of alert assignee."""
    mock_response = {
        "updateAlertsAssigneeById": {
            "alerts": [
                {**MOCK_ALERT, "assigneeId": "user-123"}
            ]
        }
    }
    
    mock_execute_query.return_value = mock_response

    result = await update_alert_assignee_by_id(["alert-123"], "user-123")

    assert result["success"] is True
    assert len(result["alerts"]) == 1

@pytest.mark.asyncio
async def test_update_alert_assignee_error(mock_execute_query):
    """Test handling of errors when updating alert assignee."""
    mock_execute_query.side_effect = Exception("Test error")

    result = await update_alert_assignee_by_id(["alert-123"], "user-123")

    assert result["success"] is False
    assert "Failed to update alert assignee" in result["message"]

@pytest.mark.asyncio
async def test_update_alert_assignee_with_empty_result(mock_execute_query):
    """Test updating alert assignee with empty result."""
    mock_response = {}  # no updateAlertsAssigneeById in result
    mock_execute_query.return_value = mock_response

    result = await update_alert_assignee_by_id(["alert-123"], "user-123")

    assert result["success"] is False
    assert "Failed to update alert assignee" in result["message"]
