import datetime
from unittest.mock import patch

import pytest

from mcp_panther.panther_mcp_core.tools.alerts import (
    add_alert_comment,
    bulk_update_alerts,
    get_alert,
    get_alert_events,
    list_alert_comments,
    list_alerts,
    start_ai_alert_triage,
    update_alert_assignee,
    update_alert_status,
)
from tests.utils.helpers import (
    patch_execute_query,
    patch_rest_client,
)

MOCK_ALERT = {
    "id": "df1eb66cede030f1a6d29362ba437178",
    "assignee": None,
    "type": "RULE",
    "title": "Derek Brooks logged into Panther",
    "createdAt": "2025-04-09T21:21:47Z",
    "firstEventOccurredAt": "2025-04-09T21:13:38Z",
    "description": "Derek Brooks logged into Panther and did some stuff",
    "reference": "https://docs.panther.com/alerts",
    "runbook": "https://docs.panther.com/alerts/alert-runbooks",
    "deliveries": [],
    "deliveryOverflow": False,
    "lastReceivedEventAt": "2025-04-09T21:21:47Z",
    "severity": "MEDIUM",
    "status": "OPEN",
    "updatedBy": None,
    "updatedAt": None,
}


MOCK_ALERTS_RESPONSE = {
    "results": [
        MOCK_ALERT,
        {**MOCK_ALERT, "id": "alert-456"},
    ],
    "next": "cursor123",
}

ALERTS_MODULE_PATH = "mcp_panther.panther_mcp_core.tools.alerts"


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_list_alerts_success(mock_rest_client):
    """Test successful listing of alerts."""
    mock_rest_client.get.return_value = (MOCK_ALERTS_RESPONSE, 200)

    result = await list_alerts()
    assert result["success"] is True
    assert len(result["alerts"]) == 2
    assert result["total_alerts"] == 2
    assert result["has_next_page"] is True
    assert result["end_cursor"] == "cursor123"

    # Verify the first alert
    first_alert = result["alerts"][0]
    assert first_alert["id"] == MOCK_ALERT["id"]
    assert first_alert["severity"] == MOCK_ALERT["severity"]
    assert first_alert["status"] == "OPEN"


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_list_alerts_with_invalid_page_size(mock_rest_client):
    """Test handling of invalid page size."""
    mock_rest_client.get.return_value = (MOCK_ALERTS_RESPONSE, 200)

    # Test with page size < 1
    result = await list_alerts(page_size=0)
    assert result["success"] is False
    assert "page_size must be greater than 0" in result["message"]

    # Test with page size > 50
    await list_alerts(page_size=100)
    mock_rest_client.get.assert_called_once()
    call_args = mock_rest_client.get.call_args[1]["params"]
    assert call_args["limit"] == 50


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
@patch("mcp_panther.panther_mcp_core.client.datetime")
async def test_list_alerts_with_default_params(mock_rest_client, mock_datetime):
    # Mock the current time to be a specific date
    fixed_time = datetime.datetime(2025, 8, 20, 12, 30, 0, tzinfo=datetime.timezone.utc)
    mock_datetime.datetime.now.return_value = fixed_time
    mock_datetime.timedelta = datetime.timedelta

    mock_rest_client.get.return_value = (MOCK_ALERTS_RESPONSE, 200)
    await list_alerts()

    # Test that we called the API with the correct default parameters
    mock_rest_client.get.assert_called_once()
    call_args = mock_rest_client.get.call_args[1]["params"]
    assert "severity" not in call_args
    assert "status" not in call_args
    assert "subtypes" not in call_args
    assert "log_sources" not in call_args
    assert "log_types" not in call_args
    assert "resource_types" not in call_args
    assert "name_contains" not in call_args
    assert "event_count_min" not in call_args
    assert "event_count_max" not in call_args
    assert "detection_id" not in call_args
    assert "assignee" not in call_args
    assert call_args["limit"] == 25
    assert call_args["type"] == "ALERT"
    assert call_args["sort-dir"] == "desc"
    # Should default to past 7 days of alerts
    assert call_args["created-after"] == "2025-08-13T12:00:00.000Z"
    assert call_args["created-before"] == "2025-08-20T12:59:59.000Z"


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_list_alerts_with_filters(mock_rest_client):
    """Test listing alerts with various filters."""
    mock_rest_client.get.return_value = (MOCK_ALERTS_RESPONSE, 200)

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
    call_args = mock_rest_client.get.call_args[1]["params"]
    assert call_args["cursor"] == "next-page-plz"
    assert call_args["severity"] == ["HIGH"]
    assert call_args["status"] == ["OPEN"]
    assert call_args["created-after"] == start_date
    assert call_args["created-before"] == end_date
    assert call_args["event-count-min"] == 1
    assert call_args["event-count-max"] == 1337
    assert call_args["log-source"] == ["my-load-balancer"]
    assert call_args["log-type"] == ["AWS.ALB"]
    assert call_args["limit"] == 25
    assert call_args["resource-type"] == ["my-resource-type"]
    assert call_args["sub-type"] == ["RULE"]
    assert call_args["name-contains"] == "Test"


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_list_alerts_with_detection_id(mock_rest_client):
    """Test listing alerts with detection ID."""
    mock_rest_client.get.return_value = (MOCK_ALERTS_RESPONSE, 200)

    result = await list_alerts(detection_id="detection-123")

    assert result["success"] is True
    call_args = mock_rest_client.get.call_args[1]["params"]
    assert call_args["detection-id"] == "detection-123"

    # When detection_id is provided, date range should not be set
    assert "created-after" not in call_args
    assert "created-before" not in call_args


@pytest.mark.asyncio
async def test_list_alerts_with_invalid_alert_type():
    """Test handling of invalid alert type."""
    result = await list_alerts(alert_type="INVALID")
    assert result["success"] is False
    assert "alert_type must be one of" in result["message"]


@pytest.mark.asyncio
async def test_list_alerts_with_invalid_subtypes():
    """Test handling of invalid subtypes."""
    # Test invalid subtype for ALERT type
    result = await list_alerts(alert_type="ALERT", subtypes=["INVALID_SUBTYPE"])
    assert result["success"] is False
    assert "Invalid subtypes" in result["message"]

    # Test subtypes with SYSTEM_ERROR type
    result = await list_alerts(alert_type="SYSTEM_ERROR", subtypes=["ANY_SUBTYPE"])
    assert result["success"] is False
    assert "subtypes are not allowed" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_list_alerts_error(mock_rest_client):
    """Test handling of errors when listing alerts."""
    mock_rest_client.get.side_effect = Exception("Test error")

    result = await list_alerts()

    assert result["success"] is False
    assert "Failed to fetch alerts" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_get_alert_success(mock_rest_client):
    """Test successful retrieval of a single alert."""
    mock_rest_client.get.return_value = (MOCK_ALERT, 200)

    result = await get_alert(MOCK_ALERT["id"])

    assert result["success"] is True
    assert result["alert"]["id"] == MOCK_ALERT["id"]
    assert result["alert"]["severity"] == MOCK_ALERT["severity"]
    assert result["alert"]["status"] == MOCK_ALERT["status"]


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_get_alert_not_found(mock_rest_client):
    """Test handling of non-existent alert."""
    mock_rest_client.get.return_value = ({}, 404)

    result = await get_alert("nonexistent-alert")

    assert result["success"] is False
    assert "No alert found" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_get_alert_error(mock_rest_client):
    """Test handling of errors when getting alert by ID."""
    mock_rest_client.get.side_effect = Exception("Test error")

    result = await get_alert(MOCK_ALERT["id"])

    assert result["success"] is False
    assert "Failed to fetch alert details" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_update_alert_status_success(mock_rest_client):
    """Test successful update of alert status."""
    mock_rest_client.patch.return_value = ({}, 204)

    result = await update_alert_status([MOCK_ALERT["id"]], "TRIAGED")

    assert result["success"] is True
    assert result["alerts"] == [MOCK_ALERT["id"]]

    # Verify patch was called with correct parameters
    mock_rest_client.patch.assert_called_once()
    call_args = mock_rest_client.patch.call_args
    assert call_args[1]["json_data"]["ids"] == [MOCK_ALERT["id"]]
    assert call_args[1]["json_data"]["status"] == "TRIAGED"


@pytest.mark.asyncio
async def test_update_alert_status_invalid_status():
    """Test handling of invalid status value."""
    result = await update_alert_status([MOCK_ALERT["id"]], "INVALID_STATUS")
    assert result["success"] is False
    assert "Invalid status" in result["message"]
    assert "Must be one of" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_update_alert_status_error(mock_rest_client):
    """Test handling of errors when updating alert status."""
    mock_rest_client.patch.side_effect = Exception("Test error")

    result = await update_alert_status([MOCK_ALERT["id"]], "TRIAGED")

    assert result["success"] is False
    assert "Failed to update alert status" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_update_alert_status_not_found(mock_rest_client):
    """Test updating alert status with 404 error."""
    mock_rest_client.patch.return_value = ({}, 404)

    result = await update_alert_status([MOCK_ALERT["id"]], "TRIAGED")

    assert result["success"] is False
    assert "One or more alerts not found" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_add_alert_comment_success(mock_rest_client):
    """Test successful addition of a comment to an alert."""
    mock_comment = {
        "id": "comment-123",
        "body": "Test comment",
        "createdAt": "2024-03-20T00:00:00Z",
    }
    mock_rest_client.post.return_value = (mock_comment, 200)

    result = await add_alert_comment(MOCK_ALERT["id"], "Test comment")

    assert result["success"] is True
    assert result["comment"]["body"] == "Test comment"


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_add_alert_comment_error(mock_rest_client):
    """Test handling of errors when adding a comment."""
    mock_rest_client.post.side_effect = Exception("Test error")

    result = await add_alert_comment(MOCK_ALERT["id"], "Test comment")

    assert result["success"] is False
    assert "Failed to add alert comment" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_add_alert_comment_not_found(mock_rest_client):
    """Test adding alert comment with 404 error."""
    mock_rest_client.post.return_value = ({}, 404)

    result = await add_alert_comment(MOCK_ALERT["id"], "Test comment")

    assert result["success"] is False
    assert "Alert not found" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_update_alert_assignee_success(mock_rest_client):
    """Test successful update of alert assignee."""
    mock_rest_client.patch.return_value = ({}, 204)

    result = await update_alert_assignee([MOCK_ALERT["id"]], "user-123")

    assert result["success"] is True
    assert result["alerts"] == [MOCK_ALERT["id"]]


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_update_alert_assignee_error(mock_rest_client):
    """Test handling of errors when updating alert assignee."""
    mock_rest_client.patch.side_effect = Exception("Test error")

    result = await update_alert_assignee([MOCK_ALERT["id"]], "user-123")

    assert result["success"] is False
    assert "Failed to update alert assignee" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_update_alert_assignee_not_found(mock_rest_client):
    """Test updating alert assignee with 404 error."""
    mock_rest_client.patch.return_value = ({}, 404)

    result = await update_alert_assignee([MOCK_ALERT["id"]], "user-123")

    assert result["success"] is False
    assert "One or more alerts not found" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_get_alert_events_success(mock_rest_client):
    """Test successful retrieval of alert events."""
    mock_events = [
        {
            "p_row_id": "event-1",
            "p_event_time": "2025-04-23 17:07:00.218308897",
            "p_alert_id": "c89fe49d40e58e82d30755f59d401a93",
        },
        {
            "p_row_id": "event-2",
            "p_event_time": "2025-04-23 17:08:00.218308897",
            "p_alert_id": "c89fe49d40e58e82d30755f59d401a93",
        },
    ]
    mock_response = {"results": mock_events}

    mock_rest_client.get.return_value = (mock_response, 200)

    result = await get_alert_events(MOCK_ALERT["id"])

    assert result["success"] is True
    assert len(result["events"]) == 2
    assert result["total_events"] == 2
    assert result["events"][0]["p_row_id"] == "event-1"
    assert result["events"][1]["p_row_id"] == "event-2"

    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    assert args[0] == f"/alerts/{MOCK_ALERT['id']}/events"
    assert kwargs["params"] == {"limit": 10}


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_get_alert_events_not_found(mock_rest_client):
    """Test handling of non-existent alert when getting events."""
    mock_rest_client.get.return_value = ({}, 404)

    result = await get_alert_events("nonexistent-alert")

    assert result["success"] is False
    assert "No alert found with ID" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_get_alert_events_error(mock_rest_client):
    """Test handling of errors when getting alert events."""
    mock_rest_client.get.side_effect = Exception("Test error")

    result = await get_alert_events(MOCK_ALERT["id"])

    assert result["success"] is False
    assert "Failed to fetch alert events" in result["message"]


@pytest.mark.asyncio
async def test_get_alert_events_invalid_limit():
    """Test handling of invalid limit value."""
    result = await get_alert_events(MOCK_ALERT["id"], limit=0)

    assert result["success"] is False
    assert "limit must be greater than 0" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_get_alert_events_limit_exceeds_max(mock_rest_client):
    """Test that limit is capped at 10 when a larger value is provided."""
    mock_events = [{"p_row_id": f"event-{i}"} for i in range(1, 10)]
    mock_response = {"results": mock_events}

    mock_rest_client.get.return_value = (mock_response, 200)

    result = await get_alert_events(MOCK_ALERT["id"], limit=100)

    assert result["success"] is True

    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    assert args[0] == f"/alerts/{MOCK_ALERT['id']}/events"
    assert kwargs["params"]["limit"] == 10


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_list_alert_comments_success(mock_rest_client):
    """Test successful retrieval of alert comments."""
    mock_comments = [
        {
            "id": "c1",
            "body": "Test comment",
            "createdAt": "2024-01-01T00:00:00Z",
            "createdBy": {"id": "u1"},
            "format": "PLAIN_TEXT",
        },
        {
            "id": "c2",
            "body": "Another comment",
            "createdAt": "2024-01-02T00:00:00Z",
            "createdBy": {"id": "u2"},
            "format": "HTML",
        },
    ]
    mock_rest_client.get.return_value = ({"results": mock_comments}, 200)

    result = await list_alert_comments("alert-123")
    assert result["success"] is True
    assert result["total_comments"] == 2
    assert result["comments"] == mock_comments
    mock_rest_client.get.assert_called_once_with(
        "/alert-comments",
        params={"alert-id": "alert-123", "limit": 25},
        expected_codes=[200, 400],
    )


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_list_alert_comments_empty_results(mock_rest_client):
    """Test empty results returns success with empty list."""
    mock_rest_client.get.return_value = ({"results": []}, 200)
    result = await list_alert_comments("alert-123")
    assert result["success"] is True
    assert result["total_comments"] == 0
    assert result["comments"] == []
    mock_rest_client.get.assert_called_once()


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_list_alert_comments_400_error(mock_rest_client):
    """Test 400 error returns failure."""
    mock_rest_client.get.return_value = ({"results": []}, 400)
    result = await list_alert_comments("alert-123")
    assert result["success"] is False
    assert "Bad request" in result["message"]
    mock_rest_client.get.assert_called_once()


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_list_alert_comments_error(mock_rest_client):
    """Test error handling when REST client raises exception."""
    mock_rest_client.get.side_effect = Exception("Boom!")
    result = await list_alert_comments("alert-err")
    assert result["success"] is False
    assert "Failed to fetch alert comments" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_list_alert_comments_custom_limit(mock_rest_client):
    """Test custom limit parameter is passed correctly."""
    mock_rest_client.get.return_value = ({"results": []}, 200)
    await list_alert_comments("alert-123", limit=10)
    mock_rest_client.get.assert_called_once_with(
        "/alert-comments",
        params={"alert-id": "alert-123", "limit": 10},
        expected_codes=[200, 400],
    )


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_list_alerts_bad_request(mock_rest_client):
    """Test 400 error returns failure."""
    mock_rest_client.get.return_value = ({}, 400)
    result = await list_alerts()
    assert result["success"] is False
    assert "Bad request" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_get_alert_bad_request(mock_rest_client):
    """Test 400 error returns failure."""
    mock_rest_client.get.return_value = ({}, 400)
    result = await get_alert("alert-123")
    assert result["success"] is False
    assert "Bad request" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_update_alert_status_bad_request(mock_rest_client):
    """Test 400 error returns failure."""
    mock_rest_client.patch.return_value = ({}, 400)
    result = await update_alert_status(["alert-123"], "TRIAGED")
    assert result["success"] is False
    assert "Bad request" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_add_alert_comment_bad_request(mock_rest_client):
    """Test 400 error returns failure."""
    mock_rest_client.post.return_value = ({}, 400)
    result = await add_alert_comment("alert-123", "Test comment")
    assert result["success"] is False
    assert "Bad request" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_update_alert_assignee_bad_request(mock_rest_client):
    """Test 400 error returns failure."""
    mock_rest_client.patch.return_value = ({}, 400)
    result = await update_alert_assignee(["alert-123"], "user-123")
    assert result["success"] is False
    assert "Bad request" in result["message"]


# Tests for bulk_update_alerts
@pytest.mark.asyncio
async def test_bulk_update_alerts_validation_empty_alert_ids():
    """Test validation when no alert IDs are provided."""
    result = await bulk_update_alerts([], status="TRIAGED")
    assert result["success"] is False
    assert "At least one alert ID must be provided" in result["message"]


@pytest.mark.asyncio
async def test_bulk_update_alerts_validation_no_operations():
    """Test validation when no operations are specified."""
    result = await bulk_update_alerts(["alert-123"])
    assert result["success"] is False
    assert (
        "At least one of status, assignee_id, or comment must be provided"
        in result["message"]
    )


@pytest.mark.asyncio
async def test_bulk_update_alerts_validation_too_many_alerts():
    """Test validation when too many alert IDs are provided."""
    # Create 26 alert IDs (exceeds the 25 limit)
    alert_ids = [f"alert-{i}" for i in range(26)]
    result = await bulk_update_alerts(alert_ids, status="TRIAGED")
    assert result["success"] is False
    assert "Cannot bulk update more than 25 alerts at once" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_bulk_update_alerts_validation_max_allowed_alerts(mock_rest_client):
    """Test that exactly 25 alerts (the maximum) works correctly."""
    mock_rest_client.patch.return_value = ({}, 204)

    # Create exactly 25 alert IDs (at the limit)
    alert_ids = [f"alert-{i}" for i in range(25)]
    result = await bulk_update_alerts(alert_ids, status="TRIAGED")

    assert result["success"] is True
    assert result["results"]["status_updates"] == alert_ids
    assert result["summary"]["total_alerts"] == 25


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_bulk_update_alerts_status_only_success(mock_rest_client):
    """Test successful bulk status update only."""
    mock_rest_client.patch.return_value = ({}, 204)

    alert_ids = ["alert-123", "alert-456"]
    result = await bulk_update_alerts(alert_ids, status="TRIAGED")

    assert result["success"] is True
    assert result["results"]["status_updates"] == alert_ids
    assert result["results"]["assignee_updates"] == []
    assert result["results"]["comments_added"] == []
    assert result["results"]["failed_operations"] == []
    assert result["summary"]["status_updates_count"] == 2
    assert result["summary"]["assignee_updates_count"] == 0
    assert result["summary"]["comments_added_count"] == 0

    # Verify patch was called once for status update
    mock_rest_client.patch.assert_called_once()
    call_args = mock_rest_client.patch.call_args
    assert call_args[1]["json_data"]["ids"] == alert_ids
    assert call_args[1]["json_data"]["status"] == "TRIAGED"


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_bulk_update_alerts_assignee_only_success(mock_rest_client):
    """Test successful bulk assignee update only."""
    mock_rest_client.patch.return_value = ({}, 204)

    alert_ids = ["alert-123", "alert-456"]
    result = await bulk_update_alerts(alert_ids, assignee_id="user-789")

    assert result["success"] is True
    assert result["results"]["status_updates"] == []
    assert result["results"]["assignee_updates"] == alert_ids
    assert result["results"]["comments_added"] == []
    assert result["results"]["failed_operations"] == []
    assert result["summary"]["assignee_updates_count"] == 2

    # Verify patch was called once for assignee update
    mock_rest_client.patch.assert_called_once()
    call_args = mock_rest_client.patch.call_args
    assert call_args[1]["json_data"]["ids"] == alert_ids
    assert call_args[1]["json_data"]["assignee"] == "user-789"


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_bulk_update_alerts_comment_only_success(mock_rest_client):
    """Test successful bulk comment addition only."""
    mock_comment = {"id": "comment-123", "body": "Bulk comment"}
    mock_rest_client.post.return_value = (mock_comment, 200)

    alert_ids = ["alert-123", "alert-456"]
    result = await bulk_update_alerts(alert_ids, comment="Bulk comment")

    assert result["success"] is True
    assert result["results"]["status_updates"] == []
    assert result["results"]["assignee_updates"] == []
    assert result["results"]["comments_added"] == alert_ids
    assert result["results"]["failed_operations"] == []
    assert result["summary"]["comments_added_count"] == 2

    # Verify post was called twice for comments
    assert mock_rest_client.post.call_count == 2
    for call_args in mock_rest_client.post.call_args_list:
        assert call_args[1]["json_data"]["body"] == "Bulk comment"
        assert call_args[1]["json_data"]["format"] == "PLAIN_TEXT"


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_bulk_update_alerts_all_operations_success(mock_rest_client):
    """Test successful execution of all operations."""
    mock_comment = {"id": "comment-123", "body": "Test comment"}
    mock_rest_client.patch.return_value = ({}, 204)
    mock_rest_client.post.return_value = (mock_comment, 200)

    alert_ids = ["alert-123", "alert-456"]
    result = await bulk_update_alerts(
        alert_ids,
        status="RESOLVED",
        assignee_id="user-789",
        comment="All operations test",
    )

    assert result["success"] is True
    assert result["results"]["status_updates"] == alert_ids
    assert result["results"]["assignee_updates"] == alert_ids
    assert result["results"]["comments_added"] == alert_ids
    assert result["results"]["failed_operations"] == []
    assert result["summary"]["successful_operations"] == 6  # 2 alerts * 3 operations
    assert result["summary"]["failed_operations"] == 0

    # Verify patch called twice (status + assignee) and post called twice (comments)
    assert mock_rest_client.patch.call_count == 2
    assert mock_rest_client.post.call_count == 2


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_bulk_update_alerts_status_failure(mock_rest_client):
    """Test handling of status update failure."""
    mock_rest_client.patch.return_value = ({}, 400)

    alert_ids = ["alert-123", "alert-456"]
    result = await bulk_update_alerts(alert_ids, status="TRIAGED")

    assert result["success"] is True
    assert result["results"]["status_updates"] == []
    assert result["results"]["failed_operations"] == [
        {
            "operation": "status_update",
            "alert_ids": alert_ids,
            "error": "HTTP 400 - Failed to update status",
        }
    ]
    assert result["summary"]["failed_operations"] == 1


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_bulk_update_alerts_assignee_failure(mock_rest_client):
    """Test handling of assignee update failure."""
    mock_rest_client.patch.return_value = ({}, 404)

    alert_ids = ["alert-123"]
    result = await bulk_update_alerts(alert_ids, assignee_id="user-789")

    assert result["success"] is True
    assert result["results"]["assignee_updates"] == []
    assert result["results"]["failed_operations"] == [
        {
            "operation": "assignee_update",
            "alert_ids": alert_ids,
            "error": "HTTP 404 - Failed to update assignee",
        }
    ]


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_bulk_update_alerts_comment_partial_failure(mock_rest_client):
    """Test handling of partial comment failures."""
    mock_comment = {"id": "comment-123", "body": "Test comment"}

    # First call succeeds, second fails
    mock_rest_client.post.side_effect = [(mock_comment, 200), ({}, 404)]

    alert_ids = ["alert-123", "alert-456"]
    result = await bulk_update_alerts(alert_ids, comment="Test comment")

    assert result["success"] is True
    assert result["results"]["comments_added"] == ["alert-123"]
    assert len(result["results"]["failed_operations"]) == 1
    assert result["results"]["failed_operations"][0]["operation"] == "add_comment"
    assert result["results"]["failed_operations"][0]["alert_ids"] == ["alert-456"]
    assert result["summary"]["comments_added_count"] == 1
    assert result["summary"]["failed_operations"] == 1


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_bulk_update_alerts_mixed_success_failure(mock_rest_client):
    """Test mixed success and failure scenarios."""
    mock_comment = {"id": "comment-123", "body": "Test comment"}

    # Status update succeeds, assignee update fails, comments partially succeed
    mock_rest_client.patch.side_effect = [({}, 204), ({}, 400)]
    mock_rest_client.post.side_effect = [(mock_comment, 200), ({}, 404)]

    alert_ids = ["alert-123", "alert-456"]
    result = await bulk_update_alerts(
        alert_ids, status="RESOLVED", assignee_id="user-789", comment="Test comment"
    )

    assert result["success"] is True
    assert result["results"]["status_updates"] == alert_ids
    assert result["results"]["assignee_updates"] == []
    assert result["results"]["comments_added"] == ["alert-123"]
    assert len(result["results"]["failed_operations"]) == 2
    assert result["summary"]["successful_operations"] == 3  # status (2) + comment (1)
    assert result["summary"]["failed_operations"] == 2  # assignee + 1 comment


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_bulk_update_alerts_exception_handling(mock_rest_client):
    """Test handling of exceptions during operations."""
    mock_rest_client.patch.side_effect = Exception("Network error")

    alert_ids = ["alert-123"]
    result = await bulk_update_alerts(alert_ids, status="TRIAGED")

    assert result["success"] is True
    assert result["results"]["status_updates"] == []
    assert len(result["results"]["failed_operations"]) == 1
    assert result["results"]["failed_operations"][0]["operation"] == "status_update"
    assert "Network error" in result["results"]["failed_operations"][0]["error"]


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_bulk_update_alerts_status_exception(mock_rest_client):
    """Test handling of status update exception."""
    mock_rest_client.patch.side_effect = Exception("Status update error")

    alert_ids = ["alert-123"]
    result = await bulk_update_alerts(alert_ids, status="TRIAGED")

    assert result["success"] is True
    assert result["results"]["status_updates"] == []
    assert len(result["results"]["failed_operations"]) == 1
    assert result["results"]["failed_operations"][0]["operation"] == "status_update"
    assert "Status update error" in result["results"]["failed_operations"][0]["error"]


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_bulk_update_alerts_comment_exception(mock_rest_client):
    """Test handling of comment addition exception."""
    mock_rest_client.post.side_effect = Exception("Comment error")

    alert_ids = ["alert-123"]
    result = await bulk_update_alerts(alert_ids, comment="Test comment")

    assert result["success"] is True
    assert result["results"]["comments_added"] == []
    assert len(result["results"]["failed_operations"]) == 1
    assert result["results"]["failed_operations"][0]["operation"] == "add_comment"
    assert "Comment error" in result["results"]["failed_operations"][0]["error"]


# AI Alert Summary Tests
@pytest.mark.asyncio
@patch_execute_query(ALERTS_MODULE_PATH)
async def test_start_ai_alert_triage_success(mock_execute_query):
    """Test successful AI alert summary generation."""
    # Mock the AI summarization initiation
    mock_execute_query.side_effect = [
        # First call: aiSummarizeAlert mutation
        {"aiSummarizeAlert": {"streamId": "stream-123"}},
        # Second call: aiInferenceStream query (in progress)
        {
            "aiInferenceStream": {
                "error": None,
                "finished": False,
                "responseText": "This alert indicates",
                "streamId": "stream-123",
            }
        },
        # Third call: aiInferenceStream query (finished)
        {
            "aiInferenceStream": {
                "error": None,
                "finished": True,
                "responseText": "This alert indicates a potential security incident involving suspicious login activity. The user Derek Brooks accessed the system outside normal hours, which could suggest unauthorized access or compromised credentials. Recommended next steps: 1) Verify the user's identity, 2) Check for additional suspicious activities, 3) Consider password reset if necessary.",
                "streamId": "stream-123",
            }
        },
    ]

    result = await start_ai_alert_triage("alert-123")

    assert result["success"] is True
    assert "security incident" in result["summary"]
    assert result["stream_id"] == "stream-123"
    assert result["metadata"]["alert_id"] == "alert-123"
    assert result["metadata"]["output_length"] == "medium"
    assert isinstance(result["metadata"]["generation_time_seconds"], float)

    # Verify the GraphQL calls were made correctly
    assert mock_execute_query.call_count == 3

    # Check the AI summarization mutation call
    first_call_args = mock_execute_query.call_args_list[0]
    variables = first_call_args[0][1]
    assert variables["input"]["alertId"] == "alert-123"
    assert variables["input"]["outputLength"] == "medium"


@pytest.mark.asyncio
@patch_execute_query(ALERTS_MODULE_PATH)
async def test_start_ai_alert_triage_with_custom_params(mock_execute_query):
    """Test AI alert summary with custom parameters."""
    mock_execute_query.side_effect = [
        {"aiSummarizeAlert": {"streamId": "stream-456"}},
        {
            "aiInferenceStream": {
                "error": None,
                "finished": True,
                "responseText": "Detailed analysis of the security event.",
                "streamId": "stream-456",
            }
        },
    ]

    result = await start_ai_alert_triage(
        alert_id="alert-456",
        prompt="Focus on the network traffic patterns",
        timeout_seconds=120,
    )

    assert result["success"] is True
    assert result["summary"] == "Detailed analysis of the security event."
    assert result["metadata"]["output_length"] == "medium"  # Always medium now
    assert result["metadata"]["prompt_included"] is True

    # Check the mutation call had the custom parameters
    first_call_args = mock_execute_query.call_args_list[0]
    variables = first_call_args[0][1]
    assert variables["input"]["outputLength"] == "medium"  # Hardcoded to medium
    assert variables["input"]["prompt"] == "Focus on the network traffic patterns"


@pytest.mark.asyncio
@patch_execute_query(ALERTS_MODULE_PATH)
async def test_start_ai_alert_triage_initiation_failure(mock_execute_query):
    """Test AI alert triage when initiation fails."""
    mock_execute_query.return_value = {}  # Empty response

    result = await start_ai_alert_triage("alert-123")

    assert result["success"] is False
    assert "Failed to initiate AI triage" in result["message"]


@pytest.mark.asyncio
@patch_execute_query(ALERTS_MODULE_PATH)
async def test_start_ai_alert_triage_inference_error(mock_execute_query):
    """Test AI alert summary when inference returns an error."""
    mock_execute_query.side_effect = [
        {"aiSummarizeAlert": {"streamId": "stream-error"}},
        {
            "aiInferenceStream": {
                "error": "AI service temporarily unavailable",
                "finished": False,
                "responseText": "",
                "streamId": "stream-error",
            }
        },
    ]

    result = await start_ai_alert_triage("alert-123")

    assert result["success"] is False
    assert "AI inference failed" in result["message"]
    assert "AI service temporarily unavailable" in result["message"]
    assert result["stream_id"] == "stream-error"


@pytest.mark.asyncio
@patch_execute_query(ALERTS_MODULE_PATH)
async def test_start_ai_alert_triage_timeout(mock_execute_query):
    """Test AI alert summary timeout handling."""

    mock_execute_query.side_effect = [
        {"aiSummarizeAlert": {"streamId": "stream-timeout"}},
        # Simulate never finishing
        {
            "aiInferenceStream": {
                "error": None,
                "finished": False,
                "responseText": "Partial analysis...",
                "streamId": "stream-timeout",
            }
        },
    ]

    # Mock time.time to simulate timeout by making elapsed time exceed timeout
    with (
        patch(
            "mcp_panther.panther_mcp_core.tools.alerts.asyncio.get_event_loop"
        ) as mock_loop,
        patch("mcp_panther.panther_mcp_core.tools.alerts.asyncio.sleep"),
    ):
        # First call returns 0 (start), second call returns 0.5 (gets response), third call returns 2 (timeout)
        mock_loop.return_value.time.side_effect = [0, 0.5, 2]

        result = await start_ai_alert_triage("alert-123", timeout_seconds=1)

    assert result["success"] is False
    assert "timed out" in result["message"]
    assert result["stream_id"] == "stream-timeout"
    assert result["partial_summary"] == "Partial analysis..."


@pytest.mark.asyncio
@patch_execute_query(ALERTS_MODULE_PATH)
async def test_start_ai_alert_triage_stream_poll_failure(mock_execute_query):
    """Test AI alert summary when stream polling fails."""
    mock_execute_query.side_effect = [
        {"aiSummarizeAlert": {"streamId": "stream-123"}},
        {},  # Empty response from stream query
        {
            "aiInferenceStream": {
                "error": None,
                "finished": True,
                "responseText": "Final analysis",
                "streamId": "stream-123",
            }
        },
    ]

    result = await start_ai_alert_triage("alert-123")

    # Should eventually succeed after the failed poll
    assert result["success"] is True
    assert result["summary"] == "Final analysis"


@pytest.mark.asyncio
@patch_execute_query(ALERTS_MODULE_PATH)
async def test_start_ai_alert_triage_exception_handling(mock_execute_query):
    """Test AI alert triage exception handling."""
    mock_execute_query.side_effect = Exception("GraphQL connection error")

    result = await start_ai_alert_triage("alert-123")

    assert result["success"] is False
    assert "Failed to start AI alert triage" in result["message"]
    assert "GraphQL connection error" in result["message"]


@pytest.mark.asyncio
@patch_execute_query(ALERTS_MODULE_PATH)
async def test_start_ai_alert_triage_streaming_response_text(mock_execute_query):
    """Test that AI alert summary properly handles streaming response text."""
    mock_execute_query.side_effect = [
        {"aiSummarizeAlert": {"streamId": "stream-streaming"}},
        # First stream response - partial
        {
            "aiInferenceStream": {
                "error": None,
                "finished": False,
                "responseText": "This alert shows ",
                "streamId": "stream-streaming",
            }
        },
        # Second stream response - more complete
        {
            "aiInferenceStream": {
                "error": None,
                "finished": False,
                "responseText": "This alert shows suspicious activity ",
                "streamId": "stream-streaming",
            }
        },
        # Final response - complete
        {
            "aiInferenceStream": {
                "error": None,
                "finished": True,
                "responseText": "This alert shows suspicious activity that requires immediate investigation.",
                "streamId": "stream-streaming",
            }
        },
    ]

    result = await start_ai_alert_triage("alert-123")

    assert result["success"] is True
    assert (
        result["summary"]
        == "This alert shows suspicious activity that requires immediate investigation."
    )
    assert result["stream_id"] == "stream-streaming"


@pytest.mark.asyncio
@patch_execute_query(ALERTS_MODULE_PATH)
async def test_start_ai_alert_triage_basic_functionality(mock_execute_query):
    """Test AI alert summary basic functionality without advanced options."""
    mock_execute_query.side_effect = [
        {"aiSummarizeAlert": {"streamId": "stream-basic"}},
        {
            "aiInferenceStream": {
                "error": None,
                "finished": True,
                "responseText": "Basic analysis of the security event.",
                "streamId": "stream-basic",
            }
        },
    ]

    result = await start_ai_alert_triage(alert_id="alert-123")

    assert result["success"] is True
    assert result["summary"] == "Basic analysis of the security event."
    assert result["stream_id"] == "stream-basic"

    # Verify basic parameters were passed correctly
    first_call_args = mock_execute_query.call_args_list[0]
    variables = first_call_args[0][1]
    assert variables["input"]["alertId"] == "alert-123"
    assert variables["input"]["outputLength"] == "medium"
