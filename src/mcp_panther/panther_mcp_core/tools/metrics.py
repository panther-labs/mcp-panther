"""
Tools for interacting with Panther metrics.
"""

import logging
import re
from typing import Annotated, Any

from pydantic import BeforeValidator, Field

from ..client import (
    _execute_query,
    _get_today_date_range,
)
from ..permissions import Permission, all_perms
from ..queries import (
    METRICS_ALERTS_PER_RULE_QUERY,
    METRICS_ALERTS_PER_SEVERITY_QUERY,
    METRICS_BYTES_PROCESSED_QUERY,
)
from .registry import mcp_tool

logger = logging.getLogger("mcp-panther")


def _validate_alert_types(v: list[str]) -> list[str]:
    """Validate alert types are valid."""
    valid_types = {"Rule", "Policy"}
    for alert_type in v:
        if alert_type not in valid_types:
            raise ValueError(
                f"Invalid alert type '{alert_type}'. Must be one of: {', '.join(sorted(valid_types))}"
            )
    return v


def _validate_severities(v: list[str]) -> list[str]:
    """Validate severities are valid."""
    valid_severities = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}
    for severity in v:
        if severity not in valid_severities:
            raise ValueError(
                f"Invalid severity '{severity}'. Must be one of: {', '.join(sorted(valid_severities))}"
            )
    return v


def _validate_interval(v: int) -> int:
    """Validate interval is one of the supported values."""
    valid_intervals = {15, 30, 60, 180, 360, 720, 1440}
    if v not in valid_intervals:
        raise ValueError(
            f"Invalid interval '{v}'. Must be one of: {', '.join(map(str, sorted(valid_intervals)))}"
        )
    return v


def _validate_rule_ids(v: list[str] | None) -> list[str] | None:
    """Validate rule IDs don't contain invalid characters."""
    if v is None:
        return v

    # Rule IDs should not contain @, spaces, or special characters like #
    invalid_pattern = re.compile(r"[@\s#]")

    for rule_id in v:
        if invalid_pattern.search(rule_id):
            raise ValueError(
                f"Invalid rule ID '{rule_id}'. Rule IDs cannot contain @, spaces, or # characters."
            )

    return v


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.SUMMARY_READ),
        "readOnlyHint": True,
    }
)
async def get_severity_alert_metrics(
    start_date: Annotated[
        str | None,
        Field(
            description="Optional start date in ISO-8601 format. If provided, defaults to the start of the current day UTC.",
            examples=["2024-03-20T00:00:00Z"],
        ),
    ] = None,
    end_date: Annotated[
        str | None,
        Field(
            description="Optional end date in ISO-8601 format. If provided, defaults to the end of the current day UTC.",
            examples=["2024-03-20T00:00:00Z"],
        ),
    ] = None,
    alert_types: Annotated[
        list[str],
        BeforeValidator(_validate_alert_types),
        Field(
            description="The specific Panther alert types to get metrics for.",
            examples=[["Rule"], ["Policy"], ["Rule", "Policy"]],
        ),
    ] = ["Rule"],
    severities: Annotated[
        list[str],
        BeforeValidator(_validate_severities),
        Field(
            description="The specific Panther alert severities to get metrics for.",
            examples=[
                ["CRITICAL", "HIGH"],
                ["MEDIUM", "LOW"],
                ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"],
            ],
        ),
    ] = ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
    interval_in_minutes: Annotated[
        int,
        BeforeValidator(_validate_interval),
        Field(
            description="How data points are aggregated over time, with smaller intervals providing more granular detail of when events occurred, while larger intervals show broader trends but obscure the precise timing of incidents.",
            examples=[15, 30, 60, 180, 360, 720, 1440],
        ),
    ] = 1440,
) -> dict[str, Any]:
    """Gets alert metrics grouped by severity for rule and policy alert types within a given time period. Use this tool to identify hot spots in your alerts, and use the list_alerts tool for specific details. Keep in mind that these metrics combine errors and alerts, so there may be inconsistencies from what list_alerts returns.

    Returns:
        Dict:
        - alerts_per_severity: List of series with breakdown by severity
        - total_alerts: Total number of alerts in the period
        - start_date: Start date of the period
        - end_date: End date of the period
        - interval_in_minutes: Grouping interval for the metrics
    """
    try:
        # If start or end date is missing, use today's date range
        if not start_date or not end_date:
            default_start_date, default_end_date = _get_today_date_range()
            if not start_date:
                start_date = default_start_date
            if not end_date:
                end_date = default_end_date

        logger.info(
            f"Fetching alerts per severity metrics from {start_date} to {end_date}"
        )

        # Prepare variables for GraphQL query
        variables = {
            "input": {
                "fromDate": start_date,
                "toDate": end_date,
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
            "start_date": start_date,
            "end_date": end_date,
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
        "permissions": all_perms(Permission.SUMMARY_READ),
        "readOnlyHint": True,
    }
)
async def get_rule_alert_metrics(
    start_date: Annotated[
        str | None,
        Field(
            description="Optional start date in ISO-8601 format. If provided, defaults to the start of the current day UTC.",
            examples=["2024-03-20T00:00:00Z"],
        ),
    ] = None,
    end_date: Annotated[
        str | None,
        Field(
            description="Optional end date in ISO-8601 format. If provided, defaults to the end of the current day UTC.",
            examples=["2024-03-20T00:00:00Z"],
        ),
    ] = None,
    interval_in_minutes: Annotated[
        int,
        BeforeValidator(_validate_interval),
        Field(
            description="Intervals for aggregating data points. Smaller intervals provide more granular detail of when events occurred, while larger intervals show broader trends but obscure the precise timing of incidents.",
            examples=[15, 30, 60, 180, 360, 720, 1440],
        ),
    ] = 15,
    rule_ids: Annotated[
        list[str],
        BeforeValidator(_validate_rule_ids),
        Field(
            description="A valid JSON list of Panther rule IDs to get metrics for",
            examples=[["AppOmni.Alert.Passthrough", "Auth0.MFA.Policy.Disabled"]],
        ),
    ] = [],
) -> dict[str, Any]:
    """Gets alert metrics grouped by detection rule for ALL alert types, including alerts, detection errors, and system errors within a given time period. Use this tool to identify hot spots in alerts and use list_alerts for specific alert details.

    Returns:
        Dict:
        - alerts_per_rule: List of series with entityId, label, and value
        - total_alerts: Total number of alerts in the period
        - start_date: Start date of the period
        - end_date: End date of the period
        - interval_in_minutes: Grouping interval for the metrics
        - rule_ids: List of rule IDs if provided
    """
    try:
        # If start or end date is missing, use today's date range
        if not start_date or not end_date:
            default_start_date, default_end_date = _get_today_date_range()
            if not start_date:
                start_date = default_start_date
            if not end_date:
                end_date = default_end_date

        logger.info(f"Fetching alerts per rule metrics from {start_date} to {end_date}")

        # Prepare variables
        variables = {
            "input": {
                "fromDate": start_date,
                "toDate": end_date,
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
            "start_date": start_date,
            "end_date": end_date,
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
        "permissions": all_perms(Permission.SUMMARY_READ),
        "readOnlyHint": True,
    }
)
async def get_bytes_processed_per_log_type_and_source(
    start_date: Annotated[
        str | None,
        Field(
            description="Optional start date in ISO-8601 format. If provided, defaults to the start of the current day UTC.",
            examples=["2024-03-20T00:00:00Z"],
        ),
    ] = None,
    end_date: Annotated[
        str | None,
        Field(
            description="Optional end date in ISO-8601 format. If provided, defaults to the end of the current day UTC.",
            examples=["2024-03-20T00:00:00Z"],
        ),
    ] = None,
    interval_in_minutes: Annotated[
        int,
        BeforeValidator(_validate_interval),
        Field(
            description="How data points are aggregated over time, with smaller intervals providing more granular detail of when events occurred, while larger intervals show broader trends but obscure the precise timing of incidents.",
            examples=[60, 720, 1440],
        ),
    ] = 1440,
) -> dict[str, Any]:
    """Retrieves data ingestion metrics showing total bytes processed per log type and source, helping analyze data volume patterns.

    Returns:
        Dict:
        - success: Boolean indicating if the query was successful
        - bytes_processed: List of series with breakdown by log type and source
        - total_bytes: Total bytes processed in the period
        - start_date: Start date of the period
        - end_date: End date of the period
        - interval_in_minutes: Grouping interval for the metrics
    """
    try:
        # If start or end date is missing, use today's date range
        if not start_date or not end_date:
            default_start_date, default_end_date = _get_today_date_range()
            if not start_date:
                start_date = default_start_date
            if not end_date:
                end_date = default_end_date

        logger.info(
            f"Fetching bytes processed metrics from {start_date} to {end_date} with {interval_in_minutes} minute interval"
        )

        # Prepare variables
        variables = {
            "input": {
                "fromDate": start_date,
                "toDate": end_date,
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
            "start_date": start_date,
            "end_date": end_date,
            "interval_in_minutes": interval_in_minutes,
        }

    except Exception as e:
        logger.error(f"Failed to fetch bytes processed metrics: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch bytes processed metrics: {str(e)}",
        }
