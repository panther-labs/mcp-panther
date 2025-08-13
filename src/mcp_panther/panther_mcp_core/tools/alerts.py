"""
Tools for interacting with Panther alerts.
"""

import logging
from typing import Annotated, Any

from pydantic import BeforeValidator, Field

from ..client import (
    _get_today_date_range,
    get_rest_client,
)
from ..permissions import Permission, all_perms
from ..validators import (
    _validate_alert_api_types,
    _validate_alert_status,
    _validate_iso_date,
    _validate_severities,
    _validate_statuses,
    _validate_subtypes,
)
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
        BeforeValidator(_validate_iso_date),
        Field(
            description="Optional start date in ISO-8601 format. If provided, defaults to the start of the current day UTC.",
            examples=["2024-03-20T00:00:00Z"],
        ),
    ] = None,
    end_date: Annotated[
        str | None,
        BeforeValidator(_validate_iso_date),
        Field(
            description="Optional end date in ISO-8601 format. If provided, defaults to the end of the current day UTC.",
            examples=["2024-03-20T00:00:00Z"],
        ),
    ] = None,
    severities: Annotated[
        list[str],
        BeforeValidator(_validate_severities),
        Field(
            description="Optional list of severities to filter by",
            examples=[["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]],
        ),
    ] = ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
    statuses: Annotated[
        list[str],
        BeforeValidator(_validate_statuses),
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
            min_length=1,
            description="Optional cursor for pagination returned from a previous call",
        ),
    ] = None,
    detection_id: Annotated[
        str | None,
        Field(
            min_length=1,
            description="Optional detection ID to filter alerts by; if provided, the date range is not required",
        ),
    ] = None,
    event_count_max: Annotated[
        int | None,
        Field(
            ge=1, description="Optional maximum number of events an alert may contain"
        ),
    ] = None,
    event_count_min: Annotated[
        int,
        Field(
            ge=1, description="Optional minimum number of events an alert must contain"
        ),
    ] = 1,
    log_sources: Annotated[
        list[str],
        Field(description="Optional list of log‑source IDs to filter alerts by"),
    ] = [],
    log_types: Annotated[
        list[str],
        Field(description="Optional list of log‑type names to filter alerts by"),
    ] = [],
    name_contains: Annotated[
        str | None,
        Field(
            min_length=1, description="Optional substring to match within alert titles"
        ),
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
        list[str],
        Field(
            description="Optional list of AWS resource‑type names to filter alerts by"
        ),
    ] = [],
    subtypes: Annotated[
        list[str],
        BeforeValidator(_validate_subtypes),
        Field(
            description="Optional list of alert subtypes (valid values depend on alert_type)",
            examples=[
                ["RULE"],  # Python rules only
                ["SCHEDULED_RULE"],  # Scheduled queries only
                ["POLICY"],  # Cloud policies only
                ["RULE", "SCHEDULED_RULE"],  # Both rule types (when alert_type=ALERT)
                [
                    "RULE_ERROR",
                    "SCHEDULED_RULE_ERROR",
                ],  # When alert_type=DETECTION_ERROR
            ],
        ),
    ] = ["RULE", "SCHEDULED_RULE"],
    alert_type: Annotated[
        str,
        BeforeValidator(_validate_alert_api_types),
        Field(
            description="Type of alerts to return",
            examples=["ALERT", "DETECTION_ERROR", "SYSTEM_ERROR"],
        ),
    ] = "ALERT",
) -> dict[str, Any]:
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
async def get_alert(
    alert_id: Annotated[
        str,
        Field(min_length=1, description="The ID of the alert to fetch"),
    ],
) -> dict[str, Any]:
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
    alert_id: Annotated[
        str,
        Field(min_length=1, description="The ID of the alert to get comments for"),
    ],
    limit: Annotated[
        int,
        Field(description="Maximum number of comments to return", ge=1, le=50),
    ] = 25,
) -> dict[str, Any]:
    """Get all comments for a specific Panther alert.

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
async def update_alert_status(
    alert_ids: Annotated[
        list[str],
        Field(description="List of alert IDs to update"),
    ],
    status: Annotated[
        str,
        BeforeValidator(_validate_alert_status),
        Field(
            description="New status for the alerts",
            examples=["OPEN", "TRIAGED", "RESOLVED", "CLOSED"],
        ),
    ],
) -> dict[str, Any]:
    """Update the status of one or more Panther alerts.

    Returns:
        Dict containing:
        - success: Boolean indicating if the update was successful
        - alerts: List of updated alert IDs if successful
        - message: Error message if unsuccessful
    """
    logger.info(f"Updating status for alerts {alert_ids} to {status}")

    try:
        # Validate status (defensive programming - should also be caught by validator)
        valid_statuses = {"OPEN", "TRIAGED", "RESOLVED", "CLOSED"}
        if status not in valid_statuses:
            raise ValueError(
                f"Invalid status '{status}'. Must be one of: {', '.join(sorted(valid_statuses))}"
            )
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
async def add_alert_comment(
    alert_id: Annotated[
        str,
        Field(min_length=1, description="The ID of the alert to comment on"),
    ],
    comment: Annotated[
        str,
        Field(min_length=1, description="The comment text to add"),
    ],
) -> dict[str, Any]:
    """Add a comment to a Panther alert. Comments support Markdown formatting.

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
    alert_ids: Annotated[
        list[str],
        Field(description="List of alert IDs to update"),
    ],
    assignee_id: Annotated[
        str,
        Field(min_length=1, description="The ID of the user to assign the alerts to"),
    ],
) -> dict[str, Any]:
    """Update the assignee of one or more alerts through the assignee's ID.

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
async def get_alert_events(
    alert_id: Annotated[
        str,
        Field(min_length=1, description="The ID of the alert to get events for"),
    ],
    limit: Annotated[
        int,
        Field(description="Maximum number of events to return", ge=1, le=50),
    ] = 10,
) -> dict[str, Any]:
    """
    Get events for a specific Panther alert.
    Order of events is not guaranteed.
    This tool does not support pagination to prevent long-running, expensive queries.

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


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.ALERT_MODIFY),
        "destructiveHint": True,
        "idempotentHint": True,
    }
)
async def bulk_update_alerts(
    alert_ids: Annotated[
        list[str],
        Field(description="List of alert IDs to update (maximum 25)"),
    ],
    status: Annotated[
        str | None,
        BeforeValidator(_validate_alert_status),
        Field(
            description="Optional new status for the alerts",
            examples=["OPEN", "TRIAGED", "RESOLVED", "CLOSED"],
        ),
    ] = None,
    assignee_id: Annotated[
        str | None,
        Field(
            min_length=1,
            description="Optional ID of the user to assign the alerts to",
        ),
    ] = None,
    comment: Annotated[
        str | None,
        Field(
            min_length=1,
            description="Optional comment to add to all alerts",
        ),
    ] = None,
) -> dict[str, Any]:
    """Bulk update multiple alerts with status, assignee, and/or comment changes.

    This tool allows you to efficiently update multiple alerts at once by setting their status,
    assignee, and adding a comment. At least one of status, assignee_id, or comment must be provided.

    Returns:
        Dict containing:
        - success: Boolean indicating overall success
        - results: Dict with operation results:
            - status_updates: List of alert IDs successfully updated with new status
            - assignee_updates: List of alert IDs successfully updated with new assignee
            - comments_added: List of alert IDs that successfully received comments
            - failed_operations: List of failed operations with error details
        - summary: Dict with counts of successful and failed operations
        - message: Error message if unsuccessful
    """
    logger.info(f"Bulk updating {len(alert_ids)} alerts")

    if not alert_ids:
        return {
            "success": False,
            "message": "At least one alert ID must be provided",
        }

    if len(alert_ids) > 25:
        return {
            "success": False,
            "message": "Cannot bulk update more than 25 alerts at once",
        }

    if not any([status, assignee_id, comment]):
        return {
            "success": False,
            "message": "At least one of status, assignee_id, or comment must be provided",
        }

    try:
        results = {
            "status_updates": [],
            "assignee_updates": [],
            "comments_added": [],
            "failed_operations": [],
        }

        async with get_rest_client() as client:
            # Update status if provided
            if status:
                try:
                    logger.info(
                        f"Updating status for {len(alert_ids)} alerts to {status}"
                    )
                    body = {"ids": alert_ids, "status": status}
                    _, status_code = await client.patch(
                        "/alerts", json_data=body, expected_codes=[204, 400, 404]
                    )

                    if status_code == 204:
                        results["status_updates"] = alert_ids.copy()
                        logger.info(
                            f"Successfully updated status for {len(alert_ids)} alerts"
                        )
                    else:
                        results["failed_operations"].append(
                            {
                                "operation": "status_update",
                                "alert_ids": alert_ids,
                                "error": f"HTTP {status_code} - Failed to update status",
                            }
                        )
                        logger.error(f"Failed to update status: HTTP {status_code}")

                except Exception as e:
                    results["failed_operations"].append(
                        {
                            "operation": "status_update",
                            "alert_ids": alert_ids,
                            "error": str(e),
                        }
                    )
                    logger.error(f"Exception updating status: {str(e)}")

            # Update assignee if provided
            if assignee_id:
                try:
                    logger.info(
                        f"Updating assignee for {len(alert_ids)} alerts to {assignee_id}"
                    )
                    body = {"ids": alert_ids, "assignee": assignee_id}
                    _, status_code = await client.patch(
                        "/alerts", json_data=body, expected_codes=[204, 400, 404]
                    )

                    if status_code == 204:
                        results["assignee_updates"] = alert_ids.copy()
                        logger.info(
                            f"Successfully updated assignee for {len(alert_ids)} alerts"
                        )
                    else:
                        results["failed_operations"].append(
                            {
                                "operation": "assignee_update",
                                "alert_ids": alert_ids,
                                "error": f"HTTP {status_code} - Failed to update assignee",
                            }
                        )
                        logger.error(f"Failed to update assignee: HTTP {status_code}")

                except Exception as e:
                    results["failed_operations"].append(
                        {
                            "operation": "assignee_update",
                            "alert_ids": alert_ids,
                            "error": str(e),
                        }
                    )
                    logger.error(f"Exception updating assignee: {str(e)}")

            # Add comment if provided
            if comment:
                successful_comments = []
                for alert_id in alert_ids:
                    try:
                        logger.debug(f"Adding comment to alert {alert_id}")
                        body = {
                            "alertId": alert_id,
                            "body": comment,
                            "format": "PLAIN_TEXT",
                        }
                        _, status_code = await client.post(
                            "/alert-comments",
                            json_data=body,
                            expected_codes=[200, 400, 404],
                        )

                        if status_code == 200:
                            successful_comments.append(alert_id)
                        else:
                            results["failed_operations"].append(
                                {
                                    "operation": "add_comment",
                                    "alert_ids": [alert_id],
                                    "error": f"HTTP {status_code} - Failed to add comment",
                                }
                            )
                            logger.error(
                                f"Failed to add comment to {alert_id}: HTTP {status_code}"
                            )

                    except Exception as e:
                        results["failed_operations"].append(
                            {
                                "operation": "add_comment",
                                "alert_ids": [alert_id],
                                "error": str(e),
                            }
                        )
                        logger.error(
                            f"Exception adding comment to {alert_id}: {str(e)}"
                        )

                results["comments_added"] = successful_comments
                logger.info(
                    f"Successfully added comments to {len(successful_comments)} alerts"
                )

        # Calculate summary statistics
        total_operations = (
            len(results["status_updates"])
            + len(results["assignee_updates"])
            + len(results["comments_added"])
        )
        total_failed = len(results["failed_operations"])

        summary = {
            "total_alerts": len(alert_ids),
            "successful_operations": total_operations,
            "failed_operations": total_failed,
            "status_updates_count": len(results["status_updates"]),
            "assignee_updates_count": len(results["assignee_updates"]),
            "comments_added_count": len(results["comments_added"]),
        }

        logger.info(
            f"Bulk update completed: {total_operations} successful, {total_failed} failed"
        )

        return {
            "success": True,
            "results": results,
            "summary": summary,
        }

    except Exception as e:
        logger.error(f"Failed to bulk update alerts: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to bulk update alerts: {str(e)}",
        }
