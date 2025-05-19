"""
Tools for interacting with Panther alerts.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from ..client import (
    _create_panther_client,
    _execute_query,
    _get_today_date_range,
    get_rest_client,
)
from ..queries import (
    ADD_ALERT_COMMENT_MUTATION,
    GET_ALERT_BY_ID_QUERY,
    GET_TODAYS_ALERTS_QUERY,
    UPDATE_ALERT_STATUS_MUTATION,
    UPDATE_ALERTS_ASSIGNEE_BY_ID_MUTATION,
)
from ..types import AlertSeverity, AlertStatus, AlertSubtype, AlertType
from .registry import mcp_tool

logger = logging.getLogger("mcp-panther")


class ListAlertsInput(BaseModel):
    """Input model for listing alerts with validation."""

    model_config = ConfigDict(
        populate_by_name=True,  # Allow both camelCase and snake_case
        json_schema_extra={
            "example": {
                "start_date": "2024-03-20T00:00:00Z",
                "end_date": "2024-03-21T00:00:00Z",
                "severities": ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
                "statuses": ["OPEN", "TRIAGED", "RESOLVED", "CLOSED"],
                "page_size": 25,
                "alert_type": "ALERT",
            }
        },
    )

    start_date: Optional[datetime] = Field(
        default=None,
        description="Start date in ISO 8601 format (e.g. '2024-03-20T00:00:00Z')",
    )
    end_date: Optional[datetime] = Field(
        default=None,
        description="End date in ISO 8601 format (e.g. '2024-03-21T00:00:00Z')",
    )
    severities: List[AlertSeverity] = Field(
        default=[
            AlertSeverity.CRITICAL,
            AlertSeverity.HIGH,
            AlertSeverity.MEDIUM,
            AlertSeverity.LOW,
        ],
        description="List of alert severities to filter alerts by",
    )
    statuses: List[AlertStatus] = Field(
        default=[
            AlertStatus.OPEN,
            AlertStatus.TRIAGED,
            AlertStatus.RESOLVED,
            AlertStatus.CLOSED,
        ],
        description="List of alert statuses to filter alerts by",
    )
    cursor: Optional[str] = Field(
        default=None, description="Cursor for pagination from a previous query"
    )
    detection_id: Optional[str] = Field(
        default=None, description="Detection ID to filter alerts by."
    )
    event_count_max: Optional[int] = Field(
        default=None,
        description="Maximum number of events that returned alerts can have",
    )
    event_count_min: Optional[int] = Field(
        default=None,
        description="Minimum number of events that returned alerts must have",
    )
    log_sources: Optional[List[str]] = Field(
        default=None, description="List of log source IDs to filter alerts by"
    )
    log_types: Optional[List[str]] = Field(
        default=None, description="List of log type names to filter alerts by"
    )
    name_contains: Optional[str] = Field(
        default=None, description="String to search for in alert titles"
    )
    page_size: int = Field(
        default=25, ge=1, le=50, description="Number of results per page"
    )
    resource_types: Optional[List[str]] = Field(
        default=None, description="List of AWS resource type names to filter alerts by"
    )
    alert_type: AlertType = Field(
        default=AlertType.ALERT, description="Type of alerts to return"
    )
    subtypes: Optional[List[AlertSubtype]] = Field(
        default=None,
        description="List of alert subtypes. Valid values depend on alert_type",
    )

    @field_validator("subtypes", mode="after")
    @classmethod
    def validate_subtypes(
        cls, v: Optional[List[Any]], info: ValidationInfo
    ) -> Optional[List[AlertSubtype]]:
        # If no subtypes are provided, return None
        if v is None:
            return v

        alert_type = info.data.get("alert_type", AlertType.ALERT)

        # Coerce all subtypes to AlertSubtype, raise if not possible
        coerced_subtypes = []
        for st in v:
            if isinstance(st, AlertSubtype):
                coerced_subtypes.append(st)
            else:
                try:
                    coerced_subtypes.append(AlertSubtype(st))
                except Exception:
                    raise ValueError(
                        f"Invalid subtype value: {st}. Must be one of: {[e.value for e in AlertSubtype]}"
                    )

        if alert_type == AlertType.SYSTEM_ERROR:
            if coerced_subtypes:
                raise ValueError(
                    "subtypes are not allowed when alert_type is SYSTEM_ERROR"
                )
            return coerced_subtypes

        # For non-SYSTEM_ERROR types, validate against allowed subtypes
        allowed_subtypes = AlertSubtype.get_valid_subtypes_for_type(alert_type)
        invalid_subtypes = [st for st in coerced_subtypes if st not in allowed_subtypes]
        if invalid_subtypes:
            raise ValueError(
                f"Invalid subtypes {invalid_subtypes} for alert_type={alert_type}. "
                f"Valid subtypes are: {allowed_subtypes}"
            )
        return coerced_subtypes


class AlertNode(BaseModel):
    """Model for an alert node in the response."""

    id: str
    title: str
    severity: str
    status: str
    created_at: str = Field(alias="createdAt")
    type: str
    description: Optional[str] = None
    reference: Optional[str] = None
    runbook: Optional[str] = None
    first_event_occurred_at: Optional[str] = Field(
        default=None, alias="firstEventOccurredAt"
    )
    last_received_event_at: Optional[str] = Field(
        default=None, alias="lastReceivedEventAt"
    )
    origin: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(
        populate_by_name=True,  # Allow both camelCase and snake_case
    )


class ListAlertsResponse(BaseModel):
    """Response model for listing alerts."""

    success: bool
    alerts: List[AlertNode]
    total_alerts: int
    has_next_page: bool
    has_previous_page: bool
    end_cursor: Optional[str] = None
    start_cursor: Optional[str] = None


@mcp_tool
async def list_alerts(list_alerts_input: ListAlertsInput) -> Dict[str, Any]:
    """List alerts from Panther with various filtering options.

    Args:
        list_alerts_input: Input parameters for listing alerts, including filters and pagination options.

    Returns:
        Dict containing:
        - success: Boolean indicating if the request was successful
        - alerts: List of alerts matching the filters
        - total_alerts: Total number of alerts returned
        - has_next_page: Boolean indicating if there are more results
        - has_previous_page: Boolean indicating if there are previous results
        - end_cursor: Cursor for the next page of results
        - start_cursor: Cursor for the previous page of results
    """
    logger.info("Fetching alerts from Panther")

    try:
        client = await _create_panther_client()

        # Prepare base input variables
        variables = {
            "input": {
                "pageSize": list_alerts_input.page_size,
                "sortBy": "createdAt",
                "sortDir": "descending",
                "type": list_alerts_input.alert_type,
            }
        }

        # Handle the required filter: either detectionId OR date range
        if list_alerts_input.detection_id:
            variables["input"]["detectionId"] = list_alerts_input.detection_id
            logger.info(f"Filtering by detection ID: {list_alerts_input.detection_id}")

        if not list_alerts_input.start_date or not list_alerts_input.end_date:
            start_date, end_date = _get_today_date_range()
            logger.info(
                f"No date range provided, using last 24 hours: {start_date} to {end_date}"
            )
        else:
            logger.info(
                f"Using provided date range: {list_alerts_input.start_date} to {list_alerts_input.end_date}"
            )

        variables["input"]["createdAtAfter"] = list_alerts_input.start_date
        variables["input"]["createdAtBefore"] = list_alerts_input.end_date

        # Add optional filters
        if list_alerts_input.cursor:
            variables["input"]["cursor"] = list_alerts_input.cursor
            logger.info(f"Using cursor for pagination: {list_alerts_input.cursor}")

        if list_alerts_input.severities:
            variables["input"]["severities"] = list_alerts_input.severities
            logger.info(f"Filtering by severities: {list_alerts_input.severities}")

        if list_alerts_input.statuses:
            variables["input"]["statuses"] = list_alerts_input.statuses
            logger.info(f"Filtering by statuses: {list_alerts_input.statuses}")

        if list_alerts_input.event_count_max is not None:
            variables["input"]["eventCountMax"] = list_alerts_input.event_count_max
            logger.info(
                f"Filtering by max event count: {list_alerts_input.event_count_max}"
            )

        if list_alerts_input.event_count_min is not None:
            variables["input"]["eventCountMin"] = list_alerts_input.event_count_min
            logger.info(
                f"Filtering by min event count: {list_alerts_input.event_count_min}"
            )

        if list_alerts_input.log_sources:
            variables["input"]["logSources"] = list_alerts_input.log_sources
            logger.info(f"Filtering by log sources: {list_alerts_input.log_sources}")

        if list_alerts_input.log_types:
            variables["input"]["logTypes"] = list_alerts_input.log_types
            logger.info(f"Filtering by log types: {list_alerts_input.log_types}")

        if list_alerts_input.name_contains:
            variables["input"]["nameContains"] = list_alerts_input.name_contains
            logger.info(
                f"Filtering by name contains: {list_alerts_input.name_contains}"
            )

        if list_alerts_input.resource_types:
            variables["input"]["resourceTypes"] = list_alerts_input.resource_types
            logger.info(
                f"Filtering by resource types: {list_alerts_input.resource_types}"
            )

        if list_alerts_input.subtypes:
            variables["input"]["subtypes"] = list_alerts_input.subtypes
            logger.info(f"Filtering by subtypes: {list_alerts_input.subtypes}")

        logger.debug(f"Query variables: {variables}")

        # Execute the query asynchronously
        async with client as session:
            result = await session.execute(
                GET_TODAYS_ALERTS_QUERY, variable_values=variables
            )

        # Log the raw result for debugging
        logger.debug(f"Raw query result: {result}")

        # Process results
        alerts_data = result.get("alerts", {})
        alert_edges = alerts_data.get("edges", [])
        page_info = alerts_data.get("pageInfo", {})

        # Extract alerts from edges and convert to AlertNode models
        alerts = [AlertNode.model_validate(edge["node"]) for edge in alert_edges]

        logger.info(f"Successfully retrieved {len(alerts)} alerts")

        # Format the response using the response model
        response = ListAlertsResponse(
            success=True,
            alerts=alerts,
            total_alerts=len(alerts),
            has_next_page=page_info.get("hasNextPage", False),
            has_previous_page=page_info.get("hasPreviousPage", False),
            end_cursor=page_info.get("endCursor"),
            start_cursor=page_info.get("startCursor"),
        )

        return response.model_dump()

    except Exception as e:
        logger.error(f"Failed to fetch alerts: {str(e)}")
        return {"success": False, "message": f"Failed to fetch alerts: {str(e)}"}


@mcp_tool
async def get_alert_by_id(alert_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific Panther alert by ID"""
    logger.info(f"Fetching alert details for ID: {alert_id}")
    try:
        client = await _create_panther_client()

        # Prepare input variables
        variables = {"id": alert_id}

        # Execute the query asynchronously
        async with client as session:
            result = await session.execute(
                GET_ALERT_BY_ID_QUERY, variable_values=variables
            )

        # Get alert data
        alert_data = result.get("alert", {})

        if not alert_data:
            logger.warning(f"No alert found with ID: {alert_id}")
            return {"success": False, "message": f"No alert found with ID: {alert_id}"}

        logger.info(f"Successfully retrieved alert details for ID: {alert_id}")

        # Format the response
        return {"success": True, "alert": alert_data}
    except Exception as e:
        logger.error(f"Failed to fetch alert details: {str(e)}")
        return {"success": False, "message": f"Failed to fetch alert details: {str(e)}"}


@mcp_tool
async def update_alert_status(alert_ids: List[str], status: str) -> Dict[str, Any]:
    """Update the status of one or more Panther alerts.

    Args:
        alert_ids: List of alert IDs to update. Can be a single ID or multiple IDs.
        status: The new status for the alerts. Must be one of:
            - "OPEN": Alert is newly created and needs investigation
            - "TRIAGED": Alert is being investigated
            - "RESOLVED": Alert has been investigated and resolved
            - "CLOSED": Alert has been closed (no further action needed)

    Returns:
        Dict containing:
        - success: Boolean indicating if the update was successful
        - alerts: List of updated alerts if successful, each containing:
            - id: The alert ID
            - status: The new status
            - updatedAt: Timestamp of the update
        - message: Error message if unsuccessful

    Example:
        # Update a single alert
        result = await update_alert_status(["alert-123"], "TRIAGED")

        # Update multiple alerts
        result = await update_alert_status(["alert-123", "alert-456"], "RESOLVED")
    """
    logger.info(f"Updating status for alerts {alert_ids} to {status}")

    try:
        # Validate status
        valid_statuses = ["OPEN", "TRIAGED", "RESOLVED", "CLOSED"]
        if status not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")

        # Prepare variables
        variables = {
            "input": {
                "ids": alert_ids,
                "status": status,
            }
        }

        # Execute mutation
        result = await _execute_query(UPDATE_ALERT_STATUS_MUTATION, variables)

        if not result or "updateAlertStatusById" not in result:
            raise Exception("Failed to update alert status")

        alerts_data = result["updateAlertStatusById"]["alerts"]

        logger.info(
            f"Successfully updated {len(alerts_data)} alerts to status {status}"
        )

        return {
            "success": True,
            "alerts": alerts_data,
        }

    except Exception as e:
        logger.error(f"Failed to update alert status: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to update alert status: {str(e)}",
        }


@mcp_tool
async def add_alert_comment(alert_id: str, comment: str) -> Dict[str, Any]:
    """Add a comment to a Panther alert. Comments support Markdown formatting.

    Args:
        alert_id: The ID of the alert to comment on
        comment: The comment text to add

    Returns:
        Dict containing:
        - success: Boolean indicating if the comment was added successfully
        - comment: Created comment information if successful
        - message: Error message if unsuccessful
    """
    logger.info(f"Adding comment to alert {alert_id}")

    try:
        # Prepare variables
        variables = {
            "input": {
                "alertId": alert_id,
                "body": comment,
            }
        }

        # Execute mutation
        result = await _execute_query(ADD_ALERT_COMMENT_MUTATION, variables)

        if not result or "createAlertComment" not in result:
            raise Exception("Failed to add alert comment")

        comment_data = result["createAlertComment"]["comment"]

        logger.info(f"Successfully added comment to alert {alert_id}")

        return {
            "success": True,
            "comment": comment_data,
        }

    except Exception as e:
        logger.error(f"Failed to add alert comment: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to add alert comment: {str(e)}",
        }


@mcp_tool
async def update_alert_assignee_by_id(
    alert_ids: List[str], assignee_id: str
) -> Dict[str, Any]:
    """Update the assignee of one or more alerts through the assignee's ID.

    Args:
        alert_ids: List of alert IDs to update
        assignee_id: The ID of the user to assign the alerts to

    Returns:
        Dict containing:
        - success: Boolean indicating if the update was successful
        - alerts: List of updated alerts if successful
        - message: Error message if unsuccessful
    """
    logger.info(f"Updating assignee for alerts {alert_ids} to user {assignee_id}")

    try:
        # Prepare variables
        variables = {
            "input": {
                "ids": alert_ids,
                "assigneeId": assignee_id,
            }
        }

        # Execute mutation
        result = await _execute_query(UPDATE_ALERTS_ASSIGNEE_BY_ID_MUTATION, variables)

        if not result or "updateAlertsAssigneeById" not in result:
            raise Exception("Failed to update alert assignee")

        alerts_data = result["updateAlertsAssigneeById"]["alerts"]

        logger.info(f"Successfully updated assignee for alerts {alert_ids}")

        return {
            "success": True,
            "alerts": alerts_data,
        }

    except Exception as e:
        logger.error(f"Failed to update alert assignee: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to update alert assignee: {str(e)}",
        }


@mcp_tool
async def get_alert_events(alert_id: str, limit: int = 10) -> Dict[str, Any]:
    """
    Get events for a specific Panther alert by ID.
    We make a best effort to return the first events for an alert, but order is not guaranteed.

    This tool does not support pagination to prevent long-running, expensive queries.

    Args:
        alert_id: The ID of the alert to get events for
        limit: Maximum number of events to return (default: 10, maximum: 10)

    Returns:
        Dict containing:
        - success: Boolean indicating if the request was successful
        - events: List of most recent events if successful
        - message: Error message if unsuccessful
    """
    logger.info(f"Fetching events for alert ID: {alert_id}")
    max_limit = 10

    try:
        if limit < 1:
            raise ValueError("limit must be greater than 0")
        if limit > max_limit:
            logger.warning(
                f"limit {limit} exceeds maximum of {max_limit}, using {max_limit} instead"
            )
            limit = max_limit

        params = {"limit": limit}

        async with get_rest_client() as client:
            result, status = await client.get(
                f"/alerts/{alert_id}/events", params=params, expected_codes=[200, 404]
            )

            if status == 404:
                logger.warning(f"No alert found with ID: {alert_id}")
                return {
                    "success": False,
                    "message": f"No alert found with ID: {alert_id}",
                }

        events = result.get("results", [])

        logger.info(
            f"Successfully retrieved {len(events)} events for alert ID: {alert_id}"
        )

        return {"success": True, "events": events, "total_events": len(events)}
    except Exception as e:
        logger.error(f"Failed to fetch alert events: {str(e)}")
        return {"success": False, "message": f"Failed to fetch alert events: {str(e)}"}
