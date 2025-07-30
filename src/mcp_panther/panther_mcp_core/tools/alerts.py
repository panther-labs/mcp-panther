"""
Tools for interacting with Panther alerts.
"""

import logging
from typing import Annotated, Any, Dict, List

from pydantic import Field

from ..client import (
    _get_today_date_range,
    get_rest_client,
)
from ..permissions import Permission, all_perms
from .registry import mcp_tool

logger = logging.getLogger("mcp-panther")


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.ALERT_READ),
        "readOnlyHint": True,
    }
)
async def list_alerts(
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
    severities: Annotated[
        List[str],
        Field(
            description="Optional list of severities to filter by",
            examples=[["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]],
        ),
    ] = ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
    statuses: Annotated[
        List[str],
        Field(
            description="Optional list of statuses to filter by",
            examples=[
                ["OPEN", "TRIAGED", "RESOLVED", "CLOSED"],
                ["RESOLVED", "CLOSED"],
                ["OPEN", "TRIAGED"],
            ],
        ),
    ] = ["OPEN", "TRIAGED", "RESOLVED", "CLOSED"],
    cursor: Annotated[
        str | None,
        Field(
            description="Optional cursor for pagination returned from a previous call"
        ),
    ] = None,
    detection_id: Annotated[
        str | None,
        Field(
            description="Optional detection ID to filter alerts by; if provided, the date range is not required"
        ),
    ] = None,
    event_count_max: Annotated[
        int | None,
        Field(description="Optional maximum number of events an alert may contain"),
    ] = None,
    event_count_min: Annotated[
        int | None,
        Field(description="Optional minimum number of events an alert must contain"),
    ] = None,
    log_sources: Annotated[
        List[str] | None,
        Field(description="Optional list of log‑source IDs to filter alerts by"),
    ] = [],
    log_types: Annotated[
        List[str] | None,
        Field(description="Optional list of log‑type names to filter alerts by"),
    ] = [],
    name_contains: Annotated[
        str | None, Field(description="Optional substring to match within alert titles")
    ] = None,
    page_size: Annotated[
        int,
        Field(
            description="Number of results per page (max 50, default 25)",
            ge=1,
            le=50,
        ),
    ] = 25,
    resource_types: Annotated[
        List[str] | None,
        Field(
            description="Optional list of AWS resource‑type names to filter alerts by"
        ),
    ] = [],
    subtypes: Annotated[
        List[str] | None,
        Field(
            description="Optional list of alert subtypes (valid values depend on alert_type)"
        ),
    ] = [],
    alert_type: Annotated[
        str,
        Field(
            description="Type of alerts to return",
            examples=["ALERT", "DETECTION_ERROR", "SYSTEM_ERROR"],
        ),
    ] = "ALERT",
) -> Dict[str, Any]:
    """List alerts from Panther with comprehensive filtering options

    Args:
        start_date: Optional start date in ISO 8601 format (e.g. "2024-03-20T00:00:00Z")
        end_date: Optional end date in ISO 8601 format (e.g. "2024-03-21T00:00:00Z")
        severities: Optional list of severities to filter by (e.g. ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"])
        statuses: Optional list of statuses to filter by (e.g. ["OPEN", "TRIAGED", "RESOLVED", "CLOSED"])
        cursor: Optional cursor for pagination from a previous query
        detection_id: Optional detection ID to filter alerts by. If provided, date range is not required.
        event_count_max: Optional maximum number of events that returned alerts must have
        event_count_min: Optional minimum number of events that returned alerts must have
        log_sources: Optional list of log source IDs to filter alerts by
        log_types: Optional list of log type names to filter alerts by
        name_contains: Optional string to search for in alert titles
        page_size: Number of results per page (default: 25, maximum: 50)
        resource_types: Optional list of AWS resource type names to filter alerts by
        subtypes: Optional list of alert subtypes. Valid values depend on alert_type:
            - When alert_type="ALERT": ["POLICY", "RULE", "SCHEDULED_RULE"]
            - When alert_type="DETECTION_ERROR": ["RULE_ERROR", "SCHEDULED_RULE_ERROR"]
            - When alert_type="SYSTEM_ERROR": subtypes are not allowed
        alert_type: Type of alerts to return (default: "ALERT"). One of:
            - "ALERT": Regular detection alerts
            - "DETECTION_ERROR": Alerts from detection errors
            - "SYSTEM_ERROR": System error alerts
    """
    logger.info("Fetching alerts from Panther")

    try:
        # Validate page size
        if page_size < 1:
            raise ValueError("page_size must be greater than 0")
        if page_size > 50:
            logger.warning(
                f"page_size {page_size} exceeds maximum of 50, using 50 instead"
            )
            page_size = 50

        # Validate alert_type and subtypes combination
        valid_alert_types = ["ALERT", "DETECTION_ERROR", "SYSTEM_ERROR"]
        if alert_type not in valid_alert_types:
            raise ValueError(f"alert_type must be one of {valid_alert_types}")

        if subtypes:
            valid_subtypes = {
                "ALERT": ["POLICY", "RULE", "SCHEDULED_RULE"],
                "DETECTION_ERROR": ["RULE_ERROR", "SCHEDULED_RULE_ERROR"],
                "SYSTEM_ERROR": [],
            }
            if alert_type == "SYSTEM_ERROR":
                raise ValueError(
                    "subtypes are not allowed when alert_type is SYSTEM_ERROR"
                )

            allowed_subtypes = valid_subtypes[alert_type]
            invalid_subtypes = [st for st in subtypes if st not in allowed_subtypes]
            if invalid_subtypes:
                raise ValueError(
                    f"Invalid subtypes {invalid_subtypes} for alert_type={alert_type}. "
                    f"Valid subtypes are: {allowed_subtypes}"
                )

        # Prepare query parameters
        params = {
            "type": alert_type,
            "limit": page_size,
            "sort-dir": "desc",
        }

        # Handle the required filter: either detection-id OR date range
        if detection_id:
            params["detection-id"] = detection_id
            logger.info(f"Filtering by detection ID: {detection_id}")
        else:
            # If no detection_id, we must have a date range
            default_start_date, default_end_date = _get_today_date_range()
            if not start_date:
                start_date = default_start_date
            if not end_date:
                end_date = default_end_date

            params["created-after"] = start_date
            params["created-before"] = end_date

        # Add optional filters
        if cursor:
            if not isinstance(cursor, str):
                raise ValueError(
                    "Cursor must be a string value from previous response's next"
                )
            params["cursor"] = cursor
            logger.info(f"Using cursor for pagination: {cursor}")

        if severities:
            params["severity"] = severities
            logger.info(f"Filtering by severities: {severities}")

        if statuses:
            params["status"] = statuses
            logger.info(f"Filtering by statuses: {statuses}")

        if event_count_max is not None:
            params["event-count-max"] = event_count_max
            logger.info(f"Filtering by max event count: {event_count_max}")

        if event_count_min is not None:
            params["event-count-min"] = event_count_min
            logger.info(f"Filtering by min event count: {event_count_min}")

        if log_sources:
            params["log-source"] = log_sources
            logger.info(f"Filtering by log sources: {log_sources}")

        if log_types:
            params["log-type"] = log_types
            logger.info(f"Filtering by log types: {log_types}")

        if name_contains:
            params["name-contains"] = name_contains
            logger.info(f"Filtering by name contains: {name_contains}")

        if resource_types:
            params["resource-type"] = resource_types
            logger.info(f"Filtering by resource types: {resource_types}")

        if subtypes:
            params["sub-type"] = subtypes
            logger.info(f"Filtering by subtypes: {subtypes}")

        logger.debug(f"Query parameters: {params}")

        # Execute the REST API call
        async with get_rest_client() as client:
            result, status = await client.get(
                "/alerts", params=params, expected_codes=[200, 400]
            )

        if status == 400:
            logger.error("Bad request when fetching alerts")
            return {
                "success": False,
                "message": "Bad request when fetching alerts",
            }

        # Log the raw result for debugging
        logger.debug(f"Raw API result: {result}")

        # Process results
        alerts = result.get("results", [])
        next_cursor = result.get("next")

        logger.info(f"Successfully retrieved {len(alerts)} alerts")

        # Format the response
        return {
            "success": True,
            "alerts": alerts,
            "total_alerts": len(alerts),
            "has_next_page": next_cursor is not None,
            "has_previous_page": cursor is not None,
            "end_cursor": next_cursor,
            "start_cursor": cursor,
        }
    except Exception as e:
        logger.error(f"Failed to fetch alerts: {str(e)}")
        return {"success": False, "message": f"Failed to fetch alerts: {str(e)}"}


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.ALERT_READ),
        "readOnlyHint": True,
    }
)
async def get_alert(alert_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific Panther alert by ID"""
    logger.info(f"Fetching alert details for ID: {alert_id}")
    try:
        # Execute the REST API call
        async with get_rest_client() as client:
            alert_data, status = await client.get(
                f"/alerts/{alert_id}", expected_codes=[200, 400, 404]
            )

        if status == 404:
            logger.warning(f"No alert found with ID: {alert_id}")
            return {"success": False, "message": f"No alert found with ID: {alert_id}"}

        if status == 400:
            logger.error(f"Bad request when fetching alert ID: {alert_id}")
            return {
                "success": False,
                "message": f"Bad request when fetching alert ID: {alert_id}",
            }

        logger.info(f"Successfully retrieved alert details for ID: {alert_id}")

        # Format the response
        return {"success": True, "alert": alert_data}
    except Exception as e:
        logger.error(f"Failed to fetch alert details: {str(e)}")
        return {"success": False, "message": f"Failed to fetch alert details: {str(e)}"}


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.ALERT_READ),
        "readOnlyHint": True,
    }
)
async def list_alert_comments(
    alert_id: str,
    limit: int = 25,  # , cursor: str = None
) -> Dict[str, Any]:
    """Get all comments for a specific Panther alert by ID.

    Args:
        alert_id: The ID of the alert to get comments for
        limit: Maximum number of comments to return (default: 25)

    Returns:
        Dict containing:
        - success: Boolean indicating if the request was successful
        - comments: List of comments if successful, each containing:
            - id: The comment ID
            - body: The comment text
            - createdAt: Timestamp when the comment was created
            - createdBy: Information about the user who created the comment
            - format: The format of the comment (HTML or PLAIN_TEXT or JSON_SCHEMA)
        - message: Error message if unsuccessful
    """
    logger.info(f"Fetching comments for alert ID: {alert_id}")
    try:
        params = {"alert-id": alert_id, "limit": limit}
        async with get_rest_client() as client:
            result, status = await client.get(
                "/alert-comments",
                params=params,
                expected_codes=[200, 400],
            )

        if status == 400:
            logger.error(f"Bad request when fetching comments for alert ID: {alert_id}")
            return {
                "success": False,
                "message": f"Bad request when fetching comments for alert ID: {alert_id}",
            }

        comments = result.get("results", [])

        logger.info(
            f"Successfully retrieved {len(comments)} comments for alert ID: {alert_id}"
        )

        return {
            "success": True,
            "comments": comments,
            "total_comments": len(comments),
        }
    except Exception as e:
        logger.error(f"Failed to fetch alert comments: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch alert comments: {str(e)}",
        }


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.ALERT_MODIFY),
        "destructiveHint": True,
        "idempotentHint": True,
    }
)
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
        - alerts: List of updated alert IDs if successful
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

        # Prepare request body
        body = {
            "ids": alert_ids,
            "status": status,
        }

        # Execute the REST API call
        async with get_rest_client() as client:
            result, status_code = await client.patch(
                "/alerts", json_data=body, expected_codes=[204, 400, 404]
            )

        if status_code == 404:
            logger.error(f"One or more alerts not found: {alert_ids}")
            return {
                "success": False,
                "message": f"One or more alerts not found: {alert_ids}",
            }

        if status_code == 400:
            logger.error(f"Bad request when updating alert status: {alert_ids}")
            return {
                "success": False,
                "message": f"Bad request when updating alert status: {alert_ids}",
            }

        logger.info(f"Successfully updated {len(alert_ids)} alerts to status {status}")

        return {
            "success": True,
            "alerts": alert_ids,  # Return the IDs that were updated
        }

    except Exception as e:
        logger.error(f"Failed to update alert status: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to update alert status: {str(e)}",
        }


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.ALERT_MODIFY),
        "destructiveHint": True,
    }
)
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
        # Prepare request body
        body = {
            "alertId": alert_id,
            "body": comment,
            "format": "PLAIN_TEXT",  # Default format
        }

        # Execute the REST API call
        async with get_rest_client() as client:
            comment_data, status = await client.post(
                "/alert-comments", json_data=body, expected_codes=[200, 400, 404]
            )

        if status == 404:
            logger.error(f"Alert not found: {alert_id}")
            return {
                "success": False,
                "message": f"Alert not found: {alert_id}",
            }

        if status == 400:
            logger.error(f"Bad request when adding comment to alert {alert_id}")
            return {
                "success": False,
                "message": f"Bad request when adding comment to alert {alert_id}",
            }

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


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.ALERT_MODIFY),
        "destructiveHint": True,
        "idempotentHint": True,
    }
)
async def update_alert_assignee(
    alert_ids: List[str], assignee_id: str
) -> Dict[str, Any]:
    """Update the assignee of one or more alerts through the assignee's ID.

    Args:
        alert_ids: List of alert IDs to update
        assignee_id: The ID of the user to assign the alerts to

    Returns:
        Dict containing:
        - success: Boolean indicating if the update was successful
        - alerts: List of updated alert IDs if successful
        - message: Error message if unsuccessful
    """
    logger.info(f"Updating assignee for alerts {alert_ids} to user {assignee_id}")

    try:
        # Prepare request body
        body = {
            "ids": alert_ids,
            "assignee": assignee_id,
        }

        # Execute the REST API call
        async with get_rest_client() as client:
            result, status = await client.patch(
                "/alerts", json_data=body, expected_codes=[204, 400, 404]
            )

        if status == 404:
            logger.error(f"One or more alerts not found: {alert_ids}")
            return {
                "success": False,
                "message": f"One or more alerts not found: {alert_ids}",
            }

        if status == 400:
            logger.error(f"Bad request when updating alert assignee: {alert_ids}")
            return {
                "success": False,
                "message": f"Bad request when updating alert assignee: {alert_ids}",
            }

        logger.info(f"Successfully updated assignee for alerts {alert_ids}")

        return {
            "success": True,
            "alerts": alert_ids,  # Return the IDs that were updated
        }

    except Exception as e:
        logger.error(f"Failed to update alert assignee: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to update alert assignee: {str(e)}",
        }


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.ALERT_READ),
        "readOnlyHint": True,
    }
)
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
