from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from mcp_panther.panther_mcp_core.queries import METRICS_BYTES_PROCESSED_QUERY
from mcp_panther.panther_mcp_core.tools.metrics import (
    AlertSeverity,
    MetricAlertType,
    get_bytes_processed_per_log_type_and_source,
    get_rule_alert_metrics,
    get_severity_alert_metrics,
)
from tests.utils.helpers import patch_graphql_client

METRICS_MODULE_PATH = "mcp_panther.panther_mcp_core.client"

# Sample response data
MOCK_METRICS_RESPONSE = {
    "metrics": {
        "alertsPerRule": [
            {
                "entityId": "Cloudflare.Firewall.L7DDoS",
                "label": "Cloudflare L7 DDoS",
                "value": 100,
            },
            {
                "entityId": "AWS.GuardDuty.Disabled",
                "label": "AWS GuardDuty Disabled",
                "value": 100,
            },
        ],
        "alertsPerSeverity": [
            {
                "label": "Rule CRITICAL",
                "value": 100,
                "breakdown": {
                    "2024-03-20T00:00:00Z": 20,
                    "2024-03-20T00:01:00Z": 20,
                    "2024-03-20T00:02:00Z": 20,
                    "2024-03-20T00:03:00Z": 20,
                    "2024-03-20T00:04:00Z": 20,
                },
            },
            {
                "label": "Rule HIGH",
                "value": 100,
                "breakdown": {
                    "2024-03-20T00:00:00Z": 20,
                    "2024-03-20T00:01:00Z": 20,
                    "2024-03-20T00:02:00Z": 20,
                    "2024-03-20T00:03:00Z": 20,
                    "2024-03-20T00:04:00Z": 20,
                },
            },
        ],
        "totalAlerts": 200,
    }
}


@pytest.fixture
def mock_execute_query():
    """Fixture to mock the _execute_query function."""
    with patch("mcp_panther.panther_mcp_core.tools.metrics._execute_query") as mock:
        mock.return_value = MOCK_METRICS_RESPONSE
        yield mock


@pytest.fixture
def mock_get_today_date_range():
    """Fixture to mock the _get_today_date_range function."""
    with patch(
        "mcp_panther.panther_mcp_core.tools.metrics._get_today_date_range"
    ) as mock:
        mock.return_value = ("2024-03-20T00:00:00.000Z", "2024-03-20T23:59:59.000Z")
        yield mock


@pytest.mark.asyncio
class TestGetMetricsAlertsPerRule:
    """Test suite for get_rule_alert_metrics function."""

    async def test_default_parameters(
        self, mock_execute_query, mock_get_today_date_range
    ):
        """Test function with default parameters."""
        result = await get_rule_alert_metrics()

        assert result["success"] is True
        assert len(result["alerts_per_rule"]) == 2
        assert result["total_alerts"] == 200
        assert result["interval_in_minutes"] == 1440
        assert result["from_date"] == "2024-03-20T00:00:00.000Z"
        assert result["to_date"] == "2024-03-20T23:59:59.000Z"

        # Verify rule data structure
        rule = result["alerts_per_rule"][0]
        assert "entityId" in rule
        assert "label" in rule
        assert "value" in rule
        assert rule["value"] == 100

    async def test_get_rule_alert_metrics_with_custom_date_range(
        self, mock_execute_query
    ):
        """Test function with custom date range."""
        from_date = datetime(2024, 3, 19, 0, 0, 0, tzinfo=timezone.utc)
        to_date = datetime(2024, 3, 19, 23, 59, 59, tzinfo=timezone.utc)

        result = await get_rule_alert_metrics(from_date=from_date, to_date=to_date)

        assert result["success"] is True
        assert result["from_date"] == "2024-03-19T00:00:00.000Z"
        assert result["to_date"] == "2024-03-19T23:59:59.000Z"
        mock_execute_query.assert_called_once()

    async def test_custom_interval(self, mock_execute_query, mock_get_today_date_range):
        """Test function with custom interval."""
        result = await get_rule_alert_metrics(interval_in_minutes=60)

        assert result["success"] is True
        assert result["interval_in_minutes"] == 60
        mock_execute_query.assert_called_once()

    async def test_filter_by_rule_ids(
        self, mock_execute_query, mock_get_today_date_range
    ):
        """Test function with rule ID filtering."""
        result = await get_rule_alert_metrics(rule_ids=["Cloudflare.Firewall.L7DDoS"])

        assert result["success"] is True
        assert len(result["alerts_per_rule"]) == 1
        assert result["alerts_per_rule"][0]["entityId"] == "Cloudflare.Firewall.L7DDoS"
        assert result["alerts_per_rule"][0]["value"] == 100

    async def test_error_handling(self, mock_execute_query):
        """Test error handling when query fails."""
        mock_execute_query.side_effect = Exception("API Error")

        result = await get_rule_alert_metrics()

        assert result["success"] is False
        assert "Failed to fetch alerts per rule metrics" in result["message"]

    async def test_invalid_interval_in_minutes(self, mock_execute_query):
        """Test handling of invalid interval_in_minutes values."""
        # Test with invalid interval
        with pytest.raises(
            ValueError, match="Input should be one of: 15, 30, 60, 180, 360, 720, 1440"
        ):
            await get_rule_alert_metrics(interval_in_minutes=45)

        # Test with valid interval
        result = await get_rule_alert_metrics(interval_in_minutes=60)
        assert result["success"] is True


@pytest.mark.asyncio
class TestGetMetricsAlertsPerSeverity:
    """Test suite for get_severity_alert_metrics function."""

    async def test_default_parameters(
        self, mock_execute_query, mock_get_today_date_range
    ):
        """Test function with default parameters."""
        result = await get_severity_alert_metrics()

        assert result["success"] is True
        assert len(result["alerts_per_severity"]) == 2
        assert result["total_alerts"] == 200
        assert result["interval_in_minutes"] == 1440
        assert result["from_date"] == "2024-03-20T00:00:00.000Z"
        assert result["to_date"] == "2024-03-20T23:59:59.000Z"

        # Verify severity data structure
        severity = result["alerts_per_severity"][0]
        assert "label" in severity
        assert "value" in severity
        assert "breakdown" in severity
        assert severity["value"] == 100
        assert len(severity["breakdown"]) == 5
        assert all(value == 20 for value in severity["breakdown"].values())

    async def test_get_severity_alert_metrics_with_custom_date_range(
        self, mock_execute_query
    ):
        """Test function with custom date range."""
        from_date = datetime(2024, 3, 19, 0, 0, 0, tzinfo=timezone.utc)
        to_date = datetime(2024, 3, 19, 23, 59, 59, tzinfo=timezone.utc)

        result = await get_severity_alert_metrics(from_date=from_date, to_date=to_date)

        assert result["success"] is True
        assert result["from_date"] == "2024-03-19T00:00:00.000Z"
        assert result["to_date"] == "2024-03-19T23:59:59.000Z"
        mock_execute_query.assert_called_once()

    async def test_custom_alert_types(
        self, mock_execute_query, mock_get_today_date_range
    ):
        """Test function with custom alert types."""
        result = await get_severity_alert_metrics(
            alert_types=[MetricAlertType.RULE, MetricAlertType.POLICY]
        )

        assert result["success"] is True
        assert len(result["alerts_per_severity"]) == 2
        mock_execute_query.assert_called_once()

    async def test_custom_severities(
        self, mock_execute_query, mock_get_today_date_range
    ):
        """Test function with custom severities."""
        result = await get_severity_alert_metrics(
            severities=[AlertSeverity.CRITICAL, AlertSeverity.HIGH]
        )

        assert result["success"] is True
        assert len(result["alerts_per_severity"]) == 2
        assert all(
            any(sev in item["label"] for sev in ["CRITICAL", "HIGH"])
            for item in result["alerts_per_severity"]
        )
        # Verify breakdown structure is preserved
        assert all("breakdown" in item for item in result["alerts_per_severity"])
        assert all(
            len(item["breakdown"]) == 5 for item in result["alerts_per_severity"]
        )

    async def test_error_handling(self, mock_execute_query):
        """Test error handling when query fails."""
        mock_execute_query.side_effect = Exception("API Error")

        result = await get_severity_alert_metrics()

        assert result["success"] is False
        assert "Failed to fetch alerts per severity metrics" in result["message"]

    async def test_invalid_interval_in_minutes(self, mock_execute_query):
        """Test handling of invalid interval_in_minutes values."""
        # Test with invalid interval
        with pytest.raises(
            ValueError, match="Input should be one of: 15, 30, 60, 180, 360, 720, 1440"
        ):
            await get_severity_alert_metrics(interval_in_minutes=45)

        # Test with valid interval
        result = await get_severity_alert_metrics(interval_in_minutes=60)
        assert result["success"] is True


@pytest.mark.asyncio
@patch_graphql_client(METRICS_MODULE_PATH)
async def test_get_bytes_processed_per_log_type_and_source_success(mock_graphql_client):
    """Test successful retrieval of bytes processed metrics."""
    # Mock response data
    mock_response = {
        "metrics": {
            "bytesProcessedPerSource": [
                {
                    "label": "AWS.CloudTrail",
                    "value": 1000000,
                    "breakdown": {"source1": 500000, "source2": 500000},
                },
                {
                    "label": "AWS.VPCFlow",
                    "value": 2000000,
                    "breakdown": {"source3": 1000000, "source4": 1000000},
                },
            ]
        }
    }
    mock_graphql_client.execute.return_value = mock_response

    # Test with explicit date range
    result = await get_bytes_processed_per_log_type_and_source(
        from_date="2024-03-01T00:00:00Z", to_date="2024-03-02T00:00:00Z", interval="24h"
    )

    assert result["success"] is True
    assert len(result["bytes_processed"]) == 2
    assert result["total_bytes"] == 3000000
    assert result["from_date"] == "2024-03-01T00:00:00Z"
    assert result["to_date"] == "2024-03-02T00:00:00Z"
    assert result["interval"] == "24h"

    # Verify the first series
    first_series = result["bytes_processed"][0]
    assert first_series["label"] == "AWS.CloudTrail"
    assert first_series["value"] == 1000000
    assert first_series["breakdown"] == {"source1": 500000, "source2": 500000}

    # Verify the second series
    second_series = result["bytes_processed"][1]
    assert second_series["label"] == "AWS.VPCFlow"
    assert second_series["value"] == 2000000
    assert second_series["breakdown"] == {"source3": 1000000, "source4": 1000000}

    # Verify GraphQL query was called with correct variables
    mock_graphql_client.execute.assert_called_once()
    call_args = mock_graphql_client.execute.call_args[1]["variable_values"]
    assert call_args["input"] == {
        "fromDate": "2024-03-01T00:00:00Z",
        "toDate": "2024-03-02T00:00:00Z",
        "intervalInMinutes": 1440,
    }


@pytest.mark.asyncio
@patch_graphql_client(METRICS_MODULE_PATH)
async def test_get_bytes_processed_per_log_type_and_source_default_dates(
    mock_graphql_client,
):
    """Test bytes processed metrics with default date range (today)."""
    # Mock response data
    mock_response = {
        "metrics": {
            "bytesProcessedPerSource": [
                {
                    "label": "AWS.CloudTrail",
                    "value": 1000000,
                    "breakdown": {"source1": 1000000},
                }
            ]
        }
    }
    mock_graphql_client.execute.return_value = mock_response

    # Test with default date range
    result = await get_bytes_processed_per_log_type_and_source()

    assert result["success"] is True
    assert len(result["bytes_processed"]) == 1
    assert result["total_bytes"] == 1000000
    assert result["interval"] == "24h"

    # Verify GraphQL query was called with today's date range
    mock_graphql_client.execute.assert_called_once()
    call_args = mock_graphql_client.execute.call_args[1]["variable_values"]
    assert "input" in call_args
    assert "fromDate" in call_args["input"]
    assert "toDate" in call_args["input"]
    assert call_args["input"]["intervalInMinutes"] == 1440


@pytest.mark.asyncio
@patch_graphql_client(METRICS_MODULE_PATH)
async def test_get_bytes_processed_per_log_type_and_source_different_intervals(
    mock_graphql_client,
):
    """Test bytes processed metrics with different interval options."""
    # Mock response data
    mock_response = {
        "metrics": {
            "bytesProcessedPerSource": [
                {
                    "label": "AWS.CloudTrail",
                    "value": 1000000,
                    "breakdown": {"source1": 1000000},
                }
            ]
        }
    }
    mock_graphql_client.execute.return_value = mock_response

    # Test with 1h interval
    result = await get_bytes_processed_per_log_type_and_source(
        from_date="2024-03-01T00:00:00Z", to_date="2024-03-01T01:00:00Z", interval="1h"
    )
    assert result["success"] is True
    assert result["interval"] == "1h"
    mock_graphql_client.execute.assert_called_with(
        METRICS_BYTES_PROCESSED_QUERY,
        variable_values={
            "input": {
                "fromDate": "2024-03-01T00:00:00Z",
                "toDate": "2024-03-01T01:00:00Z",
                "intervalInMinutes": 60,
            }
        },
    )

    # Test with 12h interval
    mock_graphql_client.reset_mock()
    result = await get_bytes_processed_per_log_type_and_source(
        from_date="2024-03-01T00:00:00Z", to_date="2024-03-01T12:00:00Z", interval="12h"
    )
    assert result["success"] is True
    assert result["interval"] == "12h"
    mock_graphql_client.execute.assert_called_with(
        METRICS_BYTES_PROCESSED_QUERY,
        variable_values={
            "input": {
                "fromDate": "2024-03-01T00:00:00Z",
                "toDate": "2024-03-01T12:00:00Z",
                "intervalInMinutes": 720,
            }
        },
    )


@pytest.mark.asyncio
@patch_graphql_client(METRICS_MODULE_PATH)
async def test_get_bytes_processed_per_log_type_and_source_error(mock_graphql_client):
    """Test error handling in bytes processed metrics."""
    # Mock GraphQL error
    mock_graphql_client.execute.side_effect = Exception("GraphQL error")

    result = await get_bytes_processed_per_log_type_and_source(
        from_date="2024-03-01T00:00:00Z", to_date="2024-03-02T00:00:00Z"
    )

    assert result["success"] is False
    assert "Failed to fetch bytes processed metrics" in result["message"]
    assert "GraphQL error" in result["message"]


@pytest.mark.asyncio
@patch_graphql_client(METRICS_MODULE_PATH)
async def test_get_bytes_processed_per_log_type_and_source_empty_response(
    mock_graphql_client,
):
    """Test handling of empty metrics response."""
    # Mock empty response
    mock_response = {"metrics": {"bytesProcessedPerSource": []}}
    mock_graphql_client.execute.return_value = mock_response

    result = await get_bytes_processed_per_log_type_and_source(
        from_date="2024-03-01T00:00:00Z", to_date="2024-03-02T00:00:00Z"
    )

    assert result["success"] is True
    assert len(result["bytes_processed"]) == 0
    assert result["total_bytes"] == 0
