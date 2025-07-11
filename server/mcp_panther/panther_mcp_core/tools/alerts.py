"""
Tools for interacting with Panther alerts.
"""

import logging
from typing import Any, Dict, List

from ..client import (
    _create_panther_client,
    _execute_query,
    _get_today_date_range,
    get_rest_client,
)
from ..permissions import Permission, all_perms
from ..queries import (
    ADD_ALERT_COMMENT_MUTATION,
    GET_ALERT_BY_ID_QUERY,
    GET_TODAYS_ALERTS_QUERY,
    UPDATE_ALERT_STATUS_MUTATION,
    UPDATE_ALERTS_ASSIGNEE_BY_ID_MUTATION,
)
from .registry import mcp_tool

logger = logging.getLogger("mcp-panther")


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.ALERT_READ),
    }
)
async def list_alerts(
    start_date: str | None = None,
    end_date: str | None = None,
    severities: List[str] = ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
    statuses: List[str] = ["OPEN", "TRIAGED", "RESOLVED", "CLOSED"],
    cursor: str | None = None,
    detection_id: str | None = None,
    event_count_max: int | None = None,
    event_count_min: int | None = None,
    log_sources: List[str] | None = None,
    log_types: List[str] | None = None,
    name_contains: str | None = None,
    page_size: int = 25,  # Default to 25, max is 50
    resource_types: List[str] | None = None,
    subtypes: List[str] | None = None,
    alert_type: str = "ALERT",  # Defaults to ALERT per schema
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
        client = await _create_panther_client()

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

        # Prepare base input variables
        variables = {
            "input": {
                "pageSize": page_size,
                "sortBy": "createdAt",
                "sortDir": "descending",
                "type": alert_type,
            }
        }

        # Handle the required filter: either detectionId OR date range
        if detection_id:
            variables["input"]["detectionId"] = detection_id
            logger.info(f"Filtering by detection ID: {detection_id}")
        else:
            # If no detection_id, we must have a date range
            # TODO(jn): Add support for relative date ranges
            if not start_date or not end_date:
                start_date, end_date = _get_today_date_range()
                logger.info(
                    f"No detection ID and missing date range, using last 24 hours: {start_date} to {end_date}"
                )
            else:
                logger.info(f"Using provided date range: {start_date} to {end_date}")

            variables["input"]["createdAtAfter"] = start_date
            variables["input"]["createdAtBefore"] = end_date

        # Add optional filters
        if cursor:
            if not isinstance(cursor, str):
                raise ValueError(
                    "Cursor must be a string value from previous response's endCursor"
                )
            variables["input"]["cursor"] = cursor
            logger.info(f"Using cursor for pagination: {cursor}")

        if severities:
            variables["input"]["severities"] = severities
            logger.info(f"Filtering by severities: {severities}")

        if statuses:
            variables["input"]["statuses"] = statuses
            logger.info(f"Filtering by statuses: {statuses}")

        if event_count_max is not None:
            variables["input"]["eventCountMax"] = event_count_max
            logger.info(f"Filtering by max event count: {event_count_max}")

        if event_count_min is not None:
            variables["input"]["eventCountMin"] = event_count_min
            logger.info(f"Filtering by min event count: {event_count_min}")

        if log_sources:
            variables["input"]["logSources"] = log_sources
            logger.info(f"Filtering by log sources: {log_sources}")

        if log_types:
            variables["input"]["logTypes"] = log_types
            logger.info(f"Filtering by log types: {log_types}")

        if name_contains:
            variables["input"]["nameContains"] = name_contains
            logger.info(f"Filtering by name contains: {name_contains}")

        if resource_types:
            variables["input"]["resourceTypes"] = resource_types
            logger.info(f"Filtering by resource types: {resource_types}")

        if subtypes:
            variables["input"]["subtypes"] = subtypes
            logger.info(f"Filtering by subtypes: {subtypes}")

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

        # Extract alerts from edges
        alerts = [edge["node"] for edge in alert_edges]

        logger.info(f"Successfully retrieved {len(alerts)} alerts")

        # Format the response
        return {
            "success": True,
            "alerts": alerts,
            "total_alerts": len(alerts),
            "has_next_page": page_info.get("hasNextPage", False),
            "has_previous_page": page_info.get("hasPreviousPage", False),
            "end_cursor": page_info.get("endCursor"),
            "start_cursor": page_info.get("startCursor"),
        }
    except Exception as e:
        logger.error(f"Failed to fetch alerts: {str(e)}")
        return {"success": False, "message": f"Failed to fetch alerts: {str(e)}"}


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.ALERT_READ),
    }
)
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


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.ALERT_READ),
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


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.ALERT_MODIFY),
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


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.ALERT_MODIFY),
    }
)
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


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.ALERT_READ),
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
