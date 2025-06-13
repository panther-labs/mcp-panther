"""
Tools for interacting with Panther metrics.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Dict

from pydantic import Field

from ..client import (
    _execute_query,
    get_today_date_range,
    graphql_date_format,
)
from ..permissions import Permission, all_perms
from ..queries import (
    METRICS_ALERTS_PER_RULE_QUERY,
    METRICS_ALERTS_PER_SEVERITY_QUERY,
    METRICS_BYTES_PROCESSED_QUERY,
)
from .registry import mcp_tool

logger = logging.getLogger("mcp-panther")


class MetricAlertType(str, Enum):
    RULE = "Rule"
    POLICY = "Policy"


class AlertSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class AlertMetricInterval(int, Enum):
    """Interval options for alert metrics in minutes."""
    FIFTEEN_MINUTES = 15
    THIRTY_MINUTES = 30
    ONE_HOUR = 60
    THREE_HOURS = 180
    SIX_HOURS = 360
    TWELVE_HOURS = 720
    ONE_DAY = 1440


class BytesProcessedInterval(int, Enum):
    """Interval options for bytes processed metrics in minutes."""
    ONE_HOUR = 60
    TWELVE_HOURS = 720
    ONE_DAY = 1440


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.METRICS_READ),
        "readOnlyHint": True,
    }
)
async def get_severity_alert_metrics(
    from_date: Annotated[
        datetime | None,
        Field(description="The start date of the metrics period."),
    ] = None,
    to_date: Annotated[
        datetime | None,
        Field(description="The end date of the metrics period."),
    ] = None,
    alert_types: Annotated[
        list[MetricAlertType],
        Field(description="The specific Panther alert types to get metrics for."),
    ] = [MetricAlertType.RULE],
    severities: Annotated[
        list[AlertSeverity],
        Field(description="The specific Panther alert severities to get metrics for."),
    ] = [
        AlertSeverity.CRITICAL,
        AlertSeverity.HIGH,
        AlertSeverity.MEDIUM,
        AlertSeverity.LOW,
    ],
    interval_in_minutes: Annotated[
        AlertMetricInterval,
        Field(
            description="How data points are aggregated over time, with smaller intervals providing more granular detail of when events occurred, while larger intervals show broader trends but obscure the precise timing of incidents."
        ),
    ] = AlertMetricInterval.ONE_DAY,
) -> Dict[str, Any]:
    """Gets alert metrics grouped by severity for rule and policy alert types within a given time period. Use this tool to identify hot spots in your alerts, and use the list_alerts tool for specific details. Keep in mind that these metrics combine errors and alerts, so there may be inconsistencies from what list_alerts returns.

    Returns:
        Dict:
        - alerts_per_severity: List of series with breakdown by severity
        - total_alerts: Total number of alerts in the period
        - from_date: Start date of the period
        - to_date: End date of the period
        - interval_in_minutes: Grouping interval for the metrics
    """
    try:
        # If from or to date is missing, use today's date range
        if not all([from_date, to_date]):
            from_date_today, to_date_today = get_today_date_range()
            logger.info(
                f"From or To date is missing, using today's date range: {from_date_today} to {to_date_today}"
            )
            if not from_date:
                from_date = from_date_today
            if not to_date:
                to_date = to_date_today
        else:
            logger.info(f"Using provided date range: {from_date} to {to_date}")

        logger.info(
            f"Fetching alerts per severity metrics from {from_date} to {to_date}"
        )

        # Prepare variables for GraphQL query
        variables = {
            "input": {
                "fromDate": graphql_date_format(from_date),
                "toDate": graphql_date_format(to_date),
                "intervalInMinutes": interval_in_minutes,
            }
        }

        # Execute GraphQL query
        result = await _execute_query(METRICS_ALERTS_PER_SEVERITY_QUERY, variables)

        if not result or "metrics" not in result:
            logger.error(f"Could not find key 'metrics' in result: {result}")
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
            "from_date": graphql_date_format(from_date),
            "to_date": graphql_date_format(to_date),
            "interval_in_minutes": interval_in_minutes,
        }

    except Exception as e:
        logger.error(f"Failed to fetch alerts per severity metrics: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch alerts per severity metrics: {str(e)}",
        }


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.METRICS_READ),
        "readOnlyHint": True,
    }
)
async def get_rule_alert_metrics(
    from_date: Annotated[
        datetime | None,
        Field(description="The start date of the metrics period."),
    ] = None,
    to_date: Annotated[
        datetime | None,
        Field(description="The end date of the metrics period."),
    ] = None,
    interval_in_minutes: Annotated[
        AlertMetricInterval,
        Field(
            description="Intervals for aggregating data points. Smaller intervals provide more granular detail of when events occurred, while larger intervals show broader trends but obscure the precise timing of incidents."
        ),
    ] = AlertMetricInterval.FIFTEEN_MINUTES,
    rule_ids: Annotated[
        list[
            Annotated[
                str,
                Field(
                    description="A Panther detection rule ID",
                    pattern=r"^[A-Za-z0-9][A-Za-z0-9!'_\-)(\'*]*(\.[A-Za-z0-9][A-Za-z0-9!'_\-)(\'*]*)*$",
                ),
            ]
        ]
        | None,
        Field(description="A valid JSON list of Panther rule IDs to get metrics for"),
    ] = None,
) -> Dict[str, Any]:
    """Gets alert metrics grouped by detection rule for ALL alert types, including alerts, detection errors, and system errors within a given time period. Use this tool to identify hot spots in alerts and use list_alerts for specific alert details.

    Returns:
        Dict:
        - alerts_per_rule: List of series with entityId, label, and value
        - total_alerts: Total number of alerts in the period
        - from_date: Start date of the period
        - to_date: End date of the period
        - interval_in_minutes: Grouping interval for the metrics
        - rule_ids: List of rule IDs if provided
    """
    try:
        # If from or to date is missing, use today's date range
        if not all([from_date, to_date]):
            from_date_today, to_date_today = get_today_date_range()
            logger.info(
                f"From or To date is missing, using today's date range: {from_date_today} to {to_date_today}"
            )
            if not from_date:
                from_date = from_date_today
            if not to_date:
                to_date = to_date_today
        else:
            logger.info(f"Using provided date range: {from_date} to {to_date}")

        logger.info(f"Fetching alerts per rule metrics from {from_date} to {to_date}")

        # Prepare variables
        variables = {
            "input": {
                "fromDate": graphql_date_format(from_date),
                "toDate": graphql_date_format(to_date),
                "intervalInMinutes": interval_in_minutes,
            }
        }

        # Execute query
        result = await _execute_query(METRICS_ALERTS_PER_RULE_QUERY, variables)

        if not result or "metrics" not in result:
            logger.error(f"Could not find key 'metrics' in result: {result}")
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
            "total_alerts": len(alerts_per_rule),
            "from_date": graphql_date_format(from_date),
            "to_date": graphql_date_format(to_date),
            "interval_in_minutes": interval_in_minutes,
            "rule_ids": rule_ids if rule_ids else None,
        }

    except Exception as e:
        logger.error(f"Failed to fetch rule alert metrics: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch rule alert metrics: {str(e)}",
        }


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.METRICS_READ),
        "readOnlyHint": True,
    }
)
async def get_bytes_processed_per_log_type_and_source(
    from_date: Annotated[
        datetime | None,
        Field(description="The start date of the metrics period."),
    ] = None,
    to_date: Annotated[
        datetime | None,
        Field(description="The end date of the metrics period."),
    ] = None,
    interval_in_minutes: Annotated[
        BytesProcessedInterval,
        Field(
            description="How data points are aggregated over time, with smaller intervals providing more granular detail of when events occurred, while larger intervals show broader trends but obscure the precise timing of incidents."
        ),
    ] = BytesProcessedInterval.ONE_DAY,
) -> Dict[str, Any]:
    """Retrieves data ingestion metrics showing total bytes processed per log type and source, helping analyze data volume patterns.

    Returns:
        Dict:
        - success: Boolean indicating if the query was successful
        - bytes_processed: List of series with breakdown by log type and source
        - total_bytes: Total bytes processed in the period
        - from_date: Start date of the period
        - to_date: End date of the period
        - interval_in_minutes: Grouping interval for the metrics
    """
    try:
        # If from or to date is missing, use today's date range
        if not all([from_date, to_date]):
            from_date_today, to_date_today = get_today_date_range()
            logger.info(
                f"From or To date is missing, using today's date range: {from_date_today} to {to_date_today}"
            )
            if not from_date:
                from_date = from_date_today
            if not to_date:
                to_date = to_date_today
        else:
            logger.info(f"Using provided date range: {from_date} to {to_date}")

        logger.info(
            f"Fetching bytes processed metrics from {from_date} to {to_date} with {interval_in_minutes} minute interval"
        )

        # Prepare variables
        variables = {
            "input": {
                "fromDate": graphql_date_format(from_date),
                "toDate": graphql_date_format(to_date),
                "intervalInMinutes": interval_in_minutes,
            }
        }

        # Execute query
        result = await _execute_query(METRICS_BYTES_PROCESSED_QUERY, variables)

        if not result or "metrics" not in result:
            logger.error(f"Could not find key 'metrics' in result: {result}")
            raise Exception("Failed to fetch metrics data")

        metrics_data = result["metrics"]
        bytes_processed = metrics_data["bytesProcessedPerSource"]

        # Calculate total bytes across all series
        total_bytes = sum(series["value"] for series in bytes_processed)

        return {
            "success": True,
            "bytes_processed": bytes_processed,
            "total_bytes": total_bytes,
            "from_date": graphql_date_format(from_date),
            "to_date": graphql_date_format(to_date),
            "interval_in_minutes": interval_in_minutes,
        }

    except Exception as e:
        logger.error(f"Failed to fetch bytes processed metrics: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch bytes processed metrics: {str(e)}",
        }
