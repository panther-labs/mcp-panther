"""
Unit tests for Panther metrics tools.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from mcp_panther.panther_mcp_core.tools.metrics import (
    get_metrics_alerts_and_errors_per_rule,
    get_metrics_alerts_and_errors_per_severity,
)

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
        mock.return_value = ("2024-03-20T00:00:00Z", "2024-03-20T23:59:59Z")
        yield mock


@pytest.mark.asyncio
class TestGetMetricsAlertsPerRule:
    """Test suite for get_metrics_alerts_and_errors_per_rule function."""

    async def test_default_parameters(
        self, mock_execute_query, mock_get_today_date_range
    ):
        """Test function with default parameters."""
        result = await get_metrics_alerts_and_errors_per_rule()

        assert result["success"] is True
        assert len(result["alerts_per_rule"]) == 2
        assert result["total_alerts"] == 200
        assert result["interval_in_minutes"] == 1440
        assert result["from_date"] == "2024-03-20T00:00:00Z"
        assert result["to_date"] == "2024-03-20T23:59:59Z"

        # Verify rule data structure
        rule = result["alerts_per_rule"][0]
        assert "entityId" in rule
        assert "label" in rule
        assert "value" in rule
        assert rule["value"] == 100

    async def test_custom_date_range(self, mock_execute_query):
        """Test function with custom date range."""
        from_date = "2024-03-19T00:00:00Z"
        to_date = "2024-03-19T23:59:59Z"

        result = await get_metrics_alerts_and_errors_per_rule(
            from_date=from_date, to_date=to_date
        )

        assert result["success"] is True
        assert result["from_date"] == from_date
        assert result["to_date"] == to_date
        mock_execute_query.assert_called_once()

    async def test_custom_interval(self, mock_execute_query, mock_get_today_date_range):
        """Test function with custom interval."""
        result = await get_metrics_alerts_and_errors_per_rule(interval_in_minutes=60)

        assert result["success"] is True
        assert result["interval_in_minutes"] == 60
        mock_execute_query.assert_called_once()

    async def test_filter_by_rule_ids(
        self, mock_execute_query, mock_get_today_date_range
    ):
        """Test function with rule ID filtering."""
        result = await get_metrics_alerts_and_errors_per_rule(
            rule_ids=["Cloudflare.Firewall.L7DDoS"]
        )

        assert result["success"] is True
        assert len(result["alerts_per_rule"]) == 1
        assert result["alerts_per_rule"][0]["entityId"] == "Cloudflare.Firewall.L7DDoS"
        assert result["alerts_per_rule"][0]["value"] == 100

    async def test_error_handling(self, mock_execute_query):
        """Test error handling when query fails."""
        mock_execute_query.side_effect = Exception("API Error")

        result = await get_metrics_alerts_and_errors_per_rule()

        assert result["success"] is False
        assert "Failed to fetch alerts per rule metrics" in result["message"]


@pytest.mark.asyncio
class TestGetMetricsAlertsPerSeverity:
    """Test suite for get_metrics_alerts_and_errors_per_severity function."""

    async def test_default_parameters(
        self, mock_execute_query, mock_get_today_date_range
    ):
        """Test function with default parameters."""
        result = await get_metrics_alerts_and_errors_per_severity()

        assert result["success"] is True
        assert len(result["alerts_per_severity"]) == 2
        assert result["total_alerts"] == 200
        assert result["interval_in_minutes"] == 1440
        assert result["from_date"] == "2024-03-20T00:00:00Z"
        assert result["to_date"] == "2024-03-20T23:59:59Z"

        # Verify severity data structure
        severity = result["alerts_per_severity"][0]
        assert "label" in severity
        assert "value" in severity
        assert "breakdown" in severity
        assert severity["value"] == 100
        assert len(severity["breakdown"]) == 5
        assert all(value == 20 for value in severity["breakdown"].values())

    async def test_custom_date_range(self, mock_execute_query):
        """Test function with custom date range."""
        from_date = "2024-03-19T00:00:00Z"
        to_date = "2024-03-19T23:59:59Z"

        result = await get_metrics_alerts_and_errors_per_severity(
            from_date=from_date, to_date=to_date
        )

        assert result["success"] is True
        assert result["from_date"] == from_date
        assert result["to_date"] == to_date
        mock_execute_query.assert_called_once()

    async def test_custom_alert_types(
        self, mock_execute_query, mock_get_today_date_range
    ):
        """Test function with custom alert types."""
        result = await get_metrics_alerts_and_errors_per_severity(
            alert_types=["Rule", "Policy"]
        )

        assert result["success"] is True
        assert len(result["alerts_per_severity"]) == 2
        mock_execute_query.assert_called_once()

    async def test_custom_severities(
        self, mock_execute_query, mock_get_today_date_range
    ):
        """Test function with custom severities."""
        result = await get_metrics_alerts_and_errors_per_severity(
            severities=["CRITICAL", "HIGH"]
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

        result = await get_metrics_alerts_and_errors_per_severity()

        assert result["success"] is False
        assert "Failed to fetch alerts per severity metrics" in result["message"]
