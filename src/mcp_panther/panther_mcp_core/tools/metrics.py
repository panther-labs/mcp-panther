"""
Tools for interacting with Panther metrics.
"""

import logging
from typing import Any, Dict, List, Literal, Optional

from ..client import _execute_query, _get_today_date_range
from ..queries import (
    METRICS_ALERTS_PER_RULE_QUERY,
    METRICS_ALERTS_PER_SEVERITY_QUERY,
    METRICS_BYTES_PROCESSED_QUERY,
)
from .registry import mcp_tool

logger = logging.getLogger("mcp-panther")


@mcp_tool
async def get_metrics_alerts_and_errors_per_severity(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    alert_types: Optional[List[str]] = ["Rule"],
    severities: Optional[List[str]] = ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
    interval_in_minutes: Optional[int] = 1440,
) -> Dict[str, Any]:
    """Gets alert metrics grouped by severity for ALL alert types including alerts, detection errors, and system errors within a given time period. Use this tool to identify hot spots in your alerts, and use the list_alerts tool for specific details.

    Args:
        from_date: Start date in ISO 8601 format (e.g. "2024-03-20T00:00:00Z"). Defaults to today at 00:00:00Z.
        to_date: End date in ISO 8601 format (e.g. "2024-03-21T00:00:00Z"). Defaults to today at 23:59:59Z.
        interval_in_minutes: The grouping interval for the metrics. Defaults to 1440 minutes (1 day) but can be set as low as 60 minutes.
        severities: Optional list of severities to filter by (e.g. ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"])
        alert_types: Optional list of alert types to filter by (e.g. ["Rule", "Policy", "Scheduled Rule", "Detection Error", "System Error"])

    Returns:
        Dict containing:
        - alerts_per_severity: List of series with breakdown by severity
        - total_alerts: Total number of alerts in the period
        - from_date: Start date of the period
        - to_date: End date of the period
        - interval_in_minutes: Grouping interval for the metrics
    """
    try:
        # If no dates provided, get today's date range
        if not from_date and not to_date:
            from_date, to_date = _get_today_date_range()
            logger.info(
                f"No date range provided, using today's date range: {from_date} to {to_date}"
            )
        else:
            logger.info(f"Using provided date range: {from_date} to {to_date}")

        logger.info(
            f"Fetching alerts per severity metrics from {from_date} to {to_date}"
        )

        # Prepare variables
        variables = {
            "input": {
                "fromDate": from_date,
                "toDate": to_date,
                "intervalInMinutes": interval_in_minutes,
            }
        }

        # Execute query
        result = await _execute_query(METRICS_ALERTS_PER_SEVERITY_QUERY, variables)

        if not result or "metrics" not in result:
            raise Exception("Failed to fetch metrics data")

        metrics_data = result["metrics"]

        # Filter metrics data by alert types and severities
        alerts_per_severity = [
            item
            for item in metrics_data["alertsPerSeverity"]
            if any(alert_type in item["label"] for alert_type in alert_types)
            and any(severity in item["label"] for severity in severities)
        ]

        return {
            "success": True,
            "alerts_per_severity": alerts_per_severity,
            "total_alerts": metrics_data["totalAlerts"],
            "from_date": from_date,
            "to_date": to_date,
            "interval_in_minutes": interval_in_minutes,
        }

    except Exception as e:
        logger.error(f"Failed to fetch alerts per severity metrics: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch alerts per severity metrics: {str(e)}",
        }


@mcp_tool
async def get_metrics_alerts_and_errors_per_rule(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    interval_in_minutes: Optional[int] = 1440,  # Default to 1 day
    rule_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Gets alert metrics per detection rule for ALL alert types including alerts, detection errors, and system errors within a given time period. Use this tool to identify hot spots in your alerts, and use the list_alerts tool for specific details.

    Args:
        from_date: Start date in ISO 8601 format (e.g. "2024-03-20T00:00:00Z"). Defaults to today at 00:00:00Z.
        to_date: End date in ISO 8601 format (e.g. "2024-03-21T00:00:00Z"). Defaults to today at 23:59:59Z.
        interval_in_minutes: The grouping interval for the metrics. Defaults to 1440 minutes (1 day) but can be set as low as 60 minutes.
        rule_ids: Optional list of rule IDs to filter results by. If not provided, returns all rules.

    Returns:
        Dict containing:
        - alerts_per_rule: Total alert count, description and entityId for each rule
        - total_alerts: Total number of alerts in the period
        - from_date: Start date of the period
        - to_date: End date of the period
        - interval_in_minutes: Grouping interval for the metrics
    """
    try:
        # If no dates provided, get today's date range
        if not from_date and not to_date:
            from_date, to_date = _get_today_date_range()
            logger.info(
                f"No date range provided, using today's date range: {from_date} to {to_date}"
            )
        else:
            logger.info(f"Using provided date range: {from_date} to {to_date}")

        logger.info(f"Fetching alerts per rule metrics from {from_date} to {to_date}")

        # Prepare variables
        variables = {
            "input": {
                "fromDate": from_date,
                "toDate": to_date,
                "intervalInMinutes": interval_in_minutes,
            }
        }

        # Execute query
        result = await _execute_query(METRICS_ALERTS_PER_RULE_QUERY, variables)

        if not result or "metrics" not in result:
            raise Exception("Failed to fetch metrics data")

        metrics_data = result["metrics"]

        # Filter by rule IDs if provided
        if rule_ids:
            alerts_per_rule = [
                item
                for item in metrics_data["alertsPerRule"]
                if item["entityId"] in rule_ids
            ]
        else:
            alerts_per_rule = metrics_data["alertsPerRule"]

        return {
            "success": True,
            "alerts_per_rule": alerts_per_rule,
            "total_alerts": metrics_data["totalAlerts"],
            "from_date": from_date,
            "to_date": to_date,
            "interval_in_minutes": interval_in_minutes,
        }

    except Exception as e:
        logger.error(f"Failed to fetch alerts per rule metrics: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch alerts per rule metrics: {str(e)}",
        }


@mcp_tool
async def get_bytes_processed_per_log_type_and_source(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    interval: Literal["1h", "12h", "24h"] = "24h",
) -> Dict[str, Any]:
    """Get the total bytes processed per log type and source for a given time period.

    This tool helps understand data ingestion patterns and costs by showing:
    1. Total bytes processed per log type
    2. Breakdown by source for each log type

    Example usage:
        # Get bytes processed for the last day
        metrics = get_bytes_processed_per_log_type_and_source(
            from_date="2024-03-01T00:00:00Z",
            to_date="2024-03-02T00:00:00Z",
            interval="24h"
        )

        # Use results to analyze ingestion patterns
        if metrics["success"]:
            for series in metrics["bytes_processed"]:
                print(f"Log type: {series['label']}")
                print(f"Total bytes: {series['value']}")
                print("Breakdown by source:")
                for source, value in series["breakdown"].items():
                    print(f"  {source}: {value} bytes")

    Args:
        from_date: Start date in ISO 8601 format (e.g. "2024-03-20T00:00:00Z"). Defaults to today at 00:00:00Z.
        to_date: End date in ISO 8601 format (e.g. "2024-03-21T00:00:00Z"). Defaults to today at 23:59:59Z.
        interval: The time interval for the metrics ("1h", "12h", or "24h"). Defaults to "24h".

    Returns:
        Dict containing:
        - success: Boolean indicating if the query was successful
        - bytes_processed: List of series with breakdown by log type and source
        - total_bytes: Total bytes processed in the period
        - from_date: Start date of the period
        - to_date: End date of the period
        - interval: The time interval used
    """
    try:
        # If no dates provided, get today's date range
        if not from_date and not to_date:
            from_date, to_date = _get_today_date_range()
            logger.info(
                f"No date range provided, using today's date range: {from_date} to {to_date}"
            )
        else:
            logger.info(f"Using provided date range: {from_date} to {to_date}")

        logger.info(
            f"Fetching bytes processed metrics from {from_date} to {to_date} with {interval} interval"
        )

        # Calculate interval in minutes based on the interval parameter
        interval_minutes = {
            "1h": 60,  # 1 hour
            "12h": 720,  # 12 hours
            "24h": 1440,  # 24 hours
        }[interval]

        # Prepare variables
        variables = {
            "input": {
                "fromDate": from_date,
                "toDate": to_date,
                "intervalInMinutes": interval_minutes,
            }
        }

        # Execute query
        result = await _execute_query(METRICS_BYTES_PROCESSED_QUERY, variables)

        if not result or "metrics" not in result:
            raise Exception("Failed to fetch metrics data")

        metrics_data = result["metrics"]
        bytes_processed = metrics_data["bytesProcessedPerSource"]

        # Calculate total bytes across all series
        total_bytes = sum(series["value"] for series in bytes_processed)

        return {
            "success": True,
            "bytes_processed": bytes_processed,
            "total_bytes": total_bytes,
            "from_date": from_date,
            "to_date": to_date,
            "interval": interval,
        }

    except Exception as e:
        logger.error(f"Failed to fetch bytes processed metrics: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch bytes processed metrics: {str(e)}",
        }
