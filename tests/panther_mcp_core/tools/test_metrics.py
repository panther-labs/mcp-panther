from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from mcp_panther.panther_mcp_core.tools.metrics import (
    AlertSeverity,
    MetricAlertType,
    get_bytes_processed_per_log_type_and_source,
    get_rule_alert_metrics,
    get_severity_alert_metrics,
)

METRICS_MODULE_PATH = "mcp_panther.panther_mcp_core.client"


@pytest.fixture
def mock_execute_query():
    """Fixture to mock the _execute_query function."""
    with patch("mcp_panther.panther_mcp_core.tools.metrics._execute_query") as mock:
        mock.return_value = {
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
        yield mock


@pytest.fixture
def mock_get_today_date_range():
    """Fixture to mock the get_today_date_range function."""
    with patch(
        "mcp_panther.panther_mcp_core.tools.metrics.get_today_date_range"
    ) as mock:
        from_date = datetime(2024, 3, 20, 0, 0, 0, tzinfo=timezone.utc)
        to_date = datetime(2024, 3, 20, 23, 59, 59, tzinfo=timezone.utc)
        mock.return_value = (from_date, to_date)
        yield mock


@pytest.mark.asyncio
class TestGetMetricsAlertsPerRule:
    """Test cases for get_rule_alert_metrics function."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self, mock_execute_query, mock_get_today_date_range):
        """Set up common mock responses."""
        # Default mock response for successful query
        mock_execute_query.return_value = {
            "metrics": {
                "alertsPerRule": [
                    {
                        "entityId": "AWS.CloudTrail.UnauthorizedAPICall",
                        "label": "AWS.CloudTrail.UnauthorizedAPICall",
                        "value": 49,
                    },
                    {
                        "entityId": "AWS.EC2.Startup.Script.Change",
                        "label": "AWS EC2 Startup Script Change",
                        "value": 48,
                    },
                    {
                        "entityId": "AWS.EC2.SecurityGroupModified",
                        "label": "AWS.EC2.SecurityGroupModified",
                        "value": 26,
                    },
                    {
                        "entityId": "AWS.EC2.RouteTableModified",
                        "label": "AWS.EC2.RouteTableModified",
                        "value": 23,
                    },
                    {
                        "entityId": "AWS.EC2.VPCModified",
                        "label": "AWS.EC2.VPCModified",
                        "value": 22,
                    },
                    {
                        "entityId": "AWS.EC2.GatewayModified",
                        "label": "AWS.EC2.GatewayModified",
                        "value": 22,
                    },
                    {
                        "entityId": "Crowdstrike.EppDetectionSummary",
                        "label": "Crowdstrike Detection Summary",
                        "value": 0,
                    },
                    {
                        "entityId": "Crowdstrike.AllowlistRemoved",
                        "label": "Crowdstrike Allowlist Removed",
                        "value": 0,
                    },
                ],
                "totalAlerts": 190,
            }
        }

        # Default mock for today's date range
        mock_get_today_date_range.return_value = (
            datetime(2024, 3, 20, 0, 0, 0, tzinfo=timezone.utc),
            datetime(2024, 3, 20, 23, 59, 59, tzinfo=timezone.utc),
        )

    async def test_default_parameters(
        self, mock_execute_query, mock_get_today_date_range
    ):
        """Test function with default parameters."""
        result = await get_rule_alert_metrics()

        assert result["success"] is True
        assert "alerts_per_rule" in result
        assert len(result["alerts_per_rule"]) == 8
        assert result["from_date"] == "2024-03-20T00:00:00.000Z"
        assert result["to_date"] == "2024-03-20T23:59:59.000Z"
        assert result["interval_in_minutes"] == 15

        # Verify mock calls
        mock_get_today_date_range.assert_called_once()
        mock_execute_query.assert_called_once()

    async def test_get_rule_alert_metrics_with_custom_date_range(
        self, mock_execute_query
    ):
        """Test function with custom date range."""
        from_date = datetime(2024, 3, 19, 0, 0, 0, tzinfo=timezone.utc)
        to_date = datetime(2024, 3, 19, 23, 59, 59, tzinfo=timezone.utc)

        result = await get_rule_alert_metrics(from_date=from_date, to_date=to_date)

        assert result["success"] is True
        assert "alerts_per_rule" in result
        assert len(result["alerts_per_rule"]) == 8
        assert result["from_date"] == "2024-03-19T00:00:00.000Z"
        assert result["to_date"] == "2024-03-19T23:59:59.000Z"

        # Verify mock calls
        mock_execute_query.assert_called_once()

    async def test_get_rule_alert_metrics_with_partial_date_range(
        self, mock_execute_query, mock_get_today_date_range
    ):
        """Test function with only one date provided."""
        from_date = datetime(2024, 3, 19, 0, 0, 0, tzinfo=timezone.utc)

        result = await get_rule_alert_metrics(from_date=from_date)

        assert result["success"] is True
        assert "alerts_per_rule" in result
        assert len(result["alerts_per_rule"]) == 8
        assert result["from_date"] == "2024-03-19T00:00:00.000Z"
        assert result["to_date"] == "2024-03-20T23:59:59.000Z"

        # Verify mock calls
        mock_get_today_date_range.assert_called_once()
        mock_execute_query.assert_called_once()

    async def test_custom_interval(self, mock_execute_query, mock_get_today_date_range):
        """Test function with custom interval."""
        result = await get_rule_alert_metrics(interval_in_minutes=60)

        assert result["success"] is True
        assert "alerts_per_rule" in result
        assert len(result["alerts_per_rule"]) == 8
        assert result["interval_in_minutes"] == 60

        # Verify mock calls
        mock_get_today_date_range.assert_called_once()
        mock_execute_query.assert_called_once()

    async def test_filter_by_rule_ids(
        self, mock_execute_query, mock_get_today_date_range
    ):
        """Test function with rule ID filtering."""
        result = await get_rule_alert_metrics(rule_ids=["AWS.EC2.RouteTableModified"])

        assert result["success"] is True
        assert "alerts_per_rule" in result
        assert len(result["alerts_per_rule"]) == 1
        assert result["rule_ids"] == ["AWS.EC2.RouteTableModified"]

        # Verify mock calls
        mock_get_today_date_range.assert_called_once()
        mock_execute_query.assert_called_once()

    async def test_error_handling(self, mock_execute_query, mock_get_today_date_range):
        """Test error handling when query fails."""
        mock_execute_query.side_effect = Exception("Query failed")

        result = await get_rule_alert_metrics()

        assert result["success"] is False
        assert "message" in result
        assert "Failed to fetch rule alert metrics" in result["message"]

        # Verify mock calls
        mock_get_today_date_range.assert_called_once()
        mock_execute_query.assert_called_once()


class TestGetMetricsAlertsPerSeverity:
    """Test suite for get_severity_alert_metrics function."""

    def setup_mocks(self, mock_execute_query, mock_get_today_date_range):
        """Set up common mock responses."""
        # Default mock response for successful query
        mock_execute_query.return_value = {
            "metrics": {
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

        # Default mock for today's date range
        mock_get_today_date_range.return_value = (
            datetime(2024, 3, 20, 0, 0, 0, tzinfo=timezone.utc),
            datetime(2024, 3, 20, 23, 59, 59, tzinfo=timezone.utc),
        )

    async def test_default_parameters(
        self, mock_execute_query, mock_get_today_date_range
    ):
        """Test function with default parameters."""
        self.setup_mocks(mock_execute_query, mock_get_today_date_range)
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
        self, mock_execute_query, mock_get_today_date_range
    ):
        """Test function with custom date range."""
        self.setup_mocks(mock_execute_query, mock_get_today_date_range)
        from_date = datetime(2024, 3, 19, 0, 0, 0, tzinfo=timezone.utc)
        to_date = datetime(2024, 3, 19, 23, 59, 59, tzinfo=timezone.utc)

        result = await get_severity_alert_metrics(from_date=from_date, to_date=to_date)

        assert result["success"] is True
        assert result["from_date"] == "2024-03-19T00:00:00.000Z"
        assert result["to_date"] == "2024-03-19T23:59:59.000Z"
        mock_execute_query.assert_called_once()

    async def test_get_severity_alert_metrics_with_partial_date_range(
        self, mock_execute_query, mock_get_today_date_range
    ):
        """Test function with only one date provided."""
        self.setup_mocks(mock_execute_query, mock_get_today_date_range)
        from_date = datetime(2024, 3, 19, 0, 0, 0, tzinfo=timezone.utc)

        result = await get_severity_alert_metrics(from_date=from_date)

        assert result["success"] is True
        assert result["from_date"] == "2024-03-19T00:00:00.000Z"
        assert result["to_date"] == "2024-03-20T23:59:59.000Z"
        mock_execute_query.assert_called_once()
        mock_get_today_date_range.assert_called_once()

    async def test_custom_alert_types(
        self, mock_execute_query, mock_get_today_date_range
    ):
        """Test function with custom alert types."""
        # Update mock response for this test
        mock_execute_query.return_value = {
            "metrics": {
                "alertsPerSeverity": [
                    {
                        "label": "Policy CRITICAL",
                        "value": 100,
                        "breakdown": {
                            "2024-03-20T00:00:00Z": 20,
                            "2024-03-20T00:01:00Z": 20,
                            "2024-03-20T00:02:00Z": 20,
                            "2024-03-20T00:03:00Z": 20,
                            "2024-03-20T00:04:00Z": 20,
                        },
                    }
                ],
                "totalAlerts": 100,
            }
        }

        result = await get_severity_alert_metrics(alert_types=[MetricAlertType.POLICY])

        assert result["success"] is True
        assert len(result["alerts_per_severity"]) == 1
        assert result["alerts_per_severity"][0]["label"] == "Policy CRITICAL"
        mock_execute_query.assert_called_once()

    async def test_custom_severities(
        self, mock_execute_query, mock_get_today_date_range
    ):
        """Test function with custom severities."""
        # Update mock response for this test
        mock_execute_query.return_value = {
            "metrics": {
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
                    }
                ],
                "totalAlerts": 100,
            }
        }

        result = await get_severity_alert_metrics(severities=[AlertSeverity.CRITICAL])

        assert result["success"] is True
        assert len(result["alerts_per_severity"]) == 1
        assert result["alerts_per_severity"][0]["label"] == "Rule CRITICAL"
        mock_execute_query.assert_called_once()

    async def test_error_handling(self, mock_execute_query, mock_get_today_date_range):
        """Test error handling when query fails."""
        self.setup_mocks(mock_execute_query, mock_get_today_date_range)
        mock_execute_query.side_effect = Exception("API Error")

        result = await get_severity_alert_metrics()

        assert result["success"] is False
        assert "Failed to fetch alerts per severity metrics" in result["message"]

    async def test_empty_alert_types(
        self, mock_execute_query, mock_get_today_date_range
    ):
        """Test function with empty alert types list."""
        # Update mock response for this test
        mock_execute_query.return_value = {
            "metrics": {
                "alertsPerSeverity": [],
                "totalAlerts": 0,
            }
        }

        result = await get_severity_alert_metrics(alert_types=[])
        assert result["success"] is True
        assert len(result["alerts_per_severity"]) == 0
        mock_execute_query.assert_called_once()

    async def test_empty_severities(
        self, mock_execute_query, mock_get_today_date_range
    ):
        """Test function with empty severities list."""
        # Update mock response for this test
        mock_execute_query.return_value = {
            "metrics": {
                "alertsPerSeverity": [],
                "totalAlerts": 0,
            }
        }

        result = await get_severity_alert_metrics(severities=[])
        assert result["success"] is True
        assert len(result["alerts_per_severity"]) == 0
        mock_execute_query.assert_called_once()

    async def test_combination_of_parameters(
        self, mock_execute_query, mock_get_today_date_range
    ):
        """Test function with combination of custom parameters."""
        self.setup_mocks(mock_execute_query, mock_get_today_date_range)
        from_date = datetime(2024, 3, 19, 0, 0, 0, tzinfo=timezone.utc)
        to_date = datetime(2024, 3, 19, 23, 59, 59, tzinfo=timezone.utc)

        # Update mock response for this test
        mock_execute_query.return_value = {
            "metrics": {
                "alertsPerSeverity": [
                    {
                        "label": "Policy CRITICAL",
                        "value": 100,
                        "breakdown": {
                            "2024-03-19T00:00:00Z": 100,
                        },
                    }
                ],
                "totalAlerts": 100,
            }
        }

        result = await get_severity_alert_metrics(
            from_date=from_date,
            to_date=to_date,
            alert_types=[MetricAlertType.POLICY],
            severities=[AlertSeverity.CRITICAL],
            interval_in_minutes=60,
        )

        assert result["success"] is True
        assert result["from_date"] == "2024-03-19T00:00:00.000Z"
        assert result["to_date"] == "2024-03-19T23:59:59.000Z"
        assert result["interval_in_minutes"] == 60
        assert len(result["alerts_per_severity"]) == 1
        assert result["alerts_per_severity"][0]["label"] == "Policy CRITICAL"
        mock_execute_query.assert_called_once()


@pytest.mark.asyncio
class TestGetBytesProcessedPerLogTypeAndSource:
    """Test suite for get_bytes_processed_per_log_type_and_source function."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self, mock_execute_query, mock_get_today_date_range):
        """Set up common mock responses."""
        # Default mock response for successful query
        mock_execute_query.return_value = {
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

        # Default mock for today's date range
        mock_get_today_date_range.return_value = (
            datetime(2024, 3, 20, 0, 0, 0, tzinfo=timezone.utc),
            datetime(2024, 3, 20, 23, 59, 59, tzinfo=timezone.utc),
        )

    async def test_default_parameters(
        self, mock_execute_query, mock_get_today_date_range
    ):
        """Test function with default parameters."""
        result = await get_bytes_processed_per_log_type_and_source()

        assert result["success"] is True
        assert len(result["bytes_processed"]) == 2
        assert result["total_bytes"] == 3000000
        assert result["interval_in_minutes"] == 1440
        assert result["from_date"] == "2024-03-20T00:00:00.000Z"
        assert result["to_date"] == "2024-03-20T23:59:59.000Z"

        # Verify first series
        first_series = result["bytes_processed"][0]
        assert first_series["label"] == "AWS.CloudTrail"
        assert first_series["value"] == 1000000
        assert first_series["breakdown"] == {"source1": 500000, "source2": 500000}

        # Verify second series
        second_series = result["bytes_processed"][1]
        assert second_series["label"] == "AWS.VPCFlow"
        assert second_series["value"] == 2000000
        assert second_series["breakdown"] == {"source3": 1000000, "source4": 1000000}

    async def test_custom_date_range(
        self, mock_execute_query, mock_get_today_date_range
    ):
        """Test function with custom date range."""
        from_date = datetime(2024, 3, 19, 0, 0, 0, tzinfo=timezone.utc)
        to_date = datetime(2024, 3, 19, 23, 59, 59, tzinfo=timezone.utc)

        result = await get_bytes_processed_per_log_type_and_source(
            from_date=from_date, to_date=to_date
        )

        assert result["success"] is True
        assert result["from_date"] == "2024-03-19T00:00:00.000Z"
        assert result["to_date"] == "2024-03-19T23:59:59.000Z"
        mock_execute_query.assert_called_once()

    async def test_partial_date_range(
        self, mock_execute_query, mock_get_today_date_range
    ):
        """Test function with only one date provided."""
        from_date = datetime(2024, 3, 19, 0, 0, 0, tzinfo=timezone.utc)

        result = await get_bytes_processed_per_log_type_and_source(from_date=from_date)

        assert result["success"] is True
        assert result["from_date"] == "2024-03-19T00:00:00.000Z"
        assert result["to_date"] == "2024-03-20T23:59:59.000Z"
        mock_execute_query.assert_called_once()
        mock_get_today_date_range.assert_called_once()

    async def test_different_intervals(
        self, mock_execute_query, mock_get_today_date_range
    ):
        """Test function with different interval options."""
        # Test with 1h interval
        result = await get_bytes_processed_per_log_type_and_source(
            from_date=datetime(2024, 3, 1, 0, 0, 0, tzinfo=timezone.utc),
            to_date=datetime(2024, 3, 1, 1, 0, 0, tzinfo=timezone.utc),
            interval_in_minutes=60,
        )
        assert result["success"] is True
        assert result["interval_in_minutes"] == 60

        # Test with 12h interval
        mock_execute_query.reset_mock()
        result = await get_bytes_processed_per_log_type_and_source(
            from_date=datetime(2024, 3, 1, 0, 0, 0, tzinfo=timezone.utc),
            to_date=datetime(2024, 3, 1, 12, 0, 0, tzinfo=timezone.utc),
            interval_in_minutes=720,
        )
        assert result["success"] is True
        assert result["interval_in_minutes"] == 720

    async def test_error_handling(self, mock_execute_query, mock_get_today_date_range):
        """Test error handling when query fails."""
        mock_execute_query.side_effect = Exception("GraphQL error")

        result = await get_bytes_processed_per_log_type_and_source(
            from_date=datetime(2024, 3, 1, 0, 0, 0, tzinfo=timezone.utc),
            to_date=datetime(2024, 3, 2, 0, 0, 0, tzinfo=timezone.utc),
        )

        assert result["success"] is False
        assert "Failed to fetch bytes processed metrics" in result["message"]
        assert "GraphQL error" in result["message"]

    async def test_empty_response(self, mock_execute_query, mock_get_today_date_range):
        """Test handling of empty metrics response."""
        mock_execute_query.return_value = {"metrics": {"bytesProcessedPerSource": []}}

        result = await get_bytes_processed_per_log_type_and_source(
            from_date=datetime(2024, 3, 1, 0, 0, 0, tzinfo=timezone.utc),
            to_date=datetime(2024, 3, 2, 0, 0, 0, tzinfo=timezone.utc),
        )

        assert result["success"] is True
        assert len(result["bytes_processed"]) == 0
        assert result["total_bytes"] == 0
