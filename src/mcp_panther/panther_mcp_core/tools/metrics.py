"""
Tools for interacting with Panther metrics.
"""

import logging
from typing import Any, Dict, List, Optional

from ..client import _execute_query, _get_today_date_range
from ..queries import METRICS_ALERTS_PER_RULE_QUERY, METRICS_ALERTS_PER_SEVERITY_QUERY
from .registry import mcp_tool

logger = logging.getLogger("mcp-panther")


@mcp_tool
async def get_metrics_alerts_per_severity(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    alert_types: Optional[List[str]] = ["Rule"],
    severities: Optional[List[str]] = ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
    interval_in_minutes: Optional[int] = 1440,
) -> Dict[str, Any]:
    """Get metrics alert counts grouped by severity. Defaults to today. Use this tool when you want to get a count of alerts by severity, alert type, or both for a given time period.

    Args:
        from_date: Optional start date in ISO 8601 format (e.g. "2024-03-20T00:00:00Z")
        to_date: Optional end date in ISO 8601 format (e.g. "2024-03-21T00:00:00Z")
        interval_in_minutes: The grouping interval for the metrics. Defaults to 1440 minutes (1 day) for daily metrics but can be set to 60 minutes (1 hour) for hourly metrics.

    Returns:
        Dict containing:
        - alerts_per_severity: List of series with breakdown by severity
        - total_alerts: Total number of alerts in the period
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
async def get_metrics_alerts_per_rule(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    interval_in_minutes: Optional[int] = 1440,  # Default to 1 day
    rule_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Returns the number of created alerts per rule during the given time period. Includes all non-error rule types like rules, scheduled rules, and policies. Use this tool when you want to get a count of alerts by rule for a given time period.

    Args:
        from_date: Optional start date in ISO 8601 format (e.g. "2024-03-20T00:00:00Z")
        to_date: Optional end date in ISO 8601 format (e.g. "2024-03-21T00:00:00Z")
        interval_in_minutes: Optional interval between metric checks (for plotting charts). Defaults to 1440 minutes (1 day).
        rule_ids: Optional list of rule IDs to filter results by. If not provided, returns all rules.

    Returns:
        Dict containing:
        - alerts_per_rule: List of series with breakdown by rule
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
