import pytest

from mcp_panther.panther_mcp_core.tools.alerts import (
    add_alert_comment,
    get_alert_by_id,
    get_alert_events,
    list_alert_comments,
    list_alerts,
    update_alert_assignee_by_id,
    update_alert_status,
)
from tests.utils.helpers import (
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
async def test_get_alert_by_id_success(mock_rest_client):
    """Test successful retrieval of a single alert."""
    mock_rest_client.get.return_value = (MOCK_ALERT, 200)

    result = await get_alert_by_id(MOCK_ALERT["id"])

    assert result["success"] is True
    assert result["alert"]["id"] == MOCK_ALERT["id"]
    assert result["alert"]["severity"] == MOCK_ALERT["severity"]
    assert result["alert"]["status"] == MOCK_ALERT["status"]


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_get_alert_by_id_not_found(mock_rest_client):
    """Test handling of non-existent alert."""
    mock_rest_client.get.return_value = ({}, 404)

    result = await get_alert_by_id("nonexistent-alert")

    assert result["success"] is False
    assert "No alert found" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_get_alert_by_id_error(mock_rest_client):
    """Test handling of errors when getting alert by ID."""
    mock_rest_client.get.side_effect = Exception("Test error")

    result = await get_alert_by_id(MOCK_ALERT["id"])

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
    assert "Status must be one of" in result["message"]


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

    result = await update_alert_assignee_by_id([MOCK_ALERT["id"]], "user-123")

    assert result["success"] is True
    assert result["alerts"] == [MOCK_ALERT["id"]]


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_update_alert_assignee_error(mock_rest_client):
    """Test handling of errors when updating alert assignee."""
    mock_rest_client.patch.side_effect = Exception("Test error")

    result = await update_alert_assignee_by_id([MOCK_ALERT["id"]], "user-123")

    assert result["success"] is False
    assert "Failed to update alert assignee" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(ALERTS_MODULE_PATH)
async def test_update_alert_assignee_not_found(mock_rest_client):
    """Test updating alert assignee with 404 error."""
    mock_rest_client.patch.return_value = ({}, 404)

    result = await update_alert_assignee_by_id([MOCK_ALERT["id"]], "user-123")

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
async def test_get_alert_by_id_bad_request(mock_rest_client):
    """Test 400 error returns failure."""
    mock_rest_client.get.return_value = ({}, 400)
    result = await get_alert_by_id("alert-123")
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
    result = await update_alert_assignee_by_id(["alert-123"], "user-123")
    assert result["success"] is False
    assert "Bad request" in result["message"]
