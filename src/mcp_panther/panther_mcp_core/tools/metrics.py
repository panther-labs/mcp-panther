"""
Tools for interacting with Panther metrics.
"""

import logging
from typing import Dict, Any, Optional

from ..client import _get_today_date_range, _execute_query
from ..queries import METRICS_ALERTS_PER_SEVERITY_QUERY, METRICS_ALERTS_PER_RULE_QUERY
from .registry import mcp_tool

logger = logging.getLogger("mcp-panther")


@mcp_tool
async def get_metrics_alerts_per_severity(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    interval_in_minutes: Optional[int] = 60,  # Default to 1 hour
) -> Dict[str, Any]:
    """Get quick metric counts of alerts grouped by severity over time.

    Args:
        from_date: Optional start date in ISO 8601 format (e.g. "2024-03-20T00:00:00Z")
        to_date: Optional end date in ISO 8601 format (e.g. "2024-03-21T00:00:00Z")
        interval_in_minutes: Optional interval between metric checks (for plotting charts). Defaults to 60 minutes (1 hour).

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

        return {
            "success": True,
            "alerts_per_severity": metrics_data["alertsPerSeverity"],
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
    interval_in_minutes: Optional[int] = 60,  # Default to 1 hour
) -> Dict[str, Any]:
    """Get quick metric counts of alerts grouped by rule over time.

    Args:
        from_date: Optional start date in ISO 8601 format (e.g. "2024-03-20T00:00:00Z")
        to_date: Optional end date in ISO 8601 format (e.g. "2024-03-21T00:00:00Z")
        interval_in_minutes: Optional interval between metric checks (for plotting charts). Defaults to 60 minutes (1 hour).

    Returns:
        Dict containing:
        - alerts_per_rule: List of series with rule IDs and alert counts
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

        return {
            "success": True,
            "alerts_per_rule": metrics_data["alertsPerRule"],
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
