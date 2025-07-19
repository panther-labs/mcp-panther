"""
Tools for interacting with Panther rules.
"""

import logging
from typing import Any, Dict, List

from typing_extensions import Annotated

from ..client import get_rest_client
from ..permissions import Permission, all_perms, any_perms
from .registry import mcp_tool

logger = logging.getLogger("mcp-panther")


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.RULE_READ, Permission.POLICY_READ),
    }
)
async def list_detections(
    detection_types: Annotated[List[str], "Types of detections to list"] = ["rules"],
    cursor: Annotated[
        str | None, "Optional cursor for pagination from a previous query"
    ] = None,
    limit: Annotated[int, "Maximum number of results to return"] = 100,
    name_contains: Annotated[
        str | None, "Substring search by name (case-insensitive)"
    ] = None,
    state: Annotated[
        str | None, "Filter by state: 'enabled' or 'disabled'"
    ] = None,
    severity: Annotated[
        List[str] | None, "Filter by severity levels: ['INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']"
    ] = None,
    tag: Annotated[
        List[str] | None, "Filter by tags (case-insensitive)"
    ] = None,
    log_type: Annotated[
        List[str] | None, "Filter by log types (for rules and simple-rules only)"
    ] = None,
    resource_type: Annotated[
        List[str] | None, "Filter by resource types (for policies only)"
    ] = None,
    compliance_status: Annotated[
        str | None, "Filter by compliance status: 'PASS', 'FAIL', or 'ERROR' (for policies only)"
    ] = None,
    created_by: Annotated[
        str | None, "Filter by creator user ID or actor ID"
    ] = None,
    last_modified_by: Annotated[
        str | None, "Filter by last modifier user ID or actor ID"
    ] = None,
) -> Dict[str, Any]:
    """List detections from your Panther instance with support for multiple detection types and filtering.

    Args:
        detection_types: Types of detections to list. Valid options: ["rules"], ["scheduled_rules"], ["simple_rules"], ["policies"]. Can specify multiple types.
        cursor: Optional cursor for pagination from a previous query (only supported for single detection type)
        limit: Maximum number of results to return per detection type (default: 100)
        name_contains: Substring search by name (case-insensitive)
        state: Filter by state - 'enabled' or 'disabled'
        severity: Filter by severity levels - list of ['INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        tag: Filter by tags (case-insensitive) - list of tag names
        log_type: Filter by log types (applies to rules and simple-rules only) - list of log type names
        resource_type: Filter by resource types (applies to policies only) - list of resource type names
        compliance_status: Filter by compliance status (applies to policies only) - 'PASS', 'FAIL', or 'ERROR'
        created_by: Filter by creator user ID or actor ID
        last_modified_by: Filter by last modifier user ID or actor ID
    """
    if not detection_types:
        return {
            "success": False,
            "message": "At least one detection type must be specified.",
        }

    logger.info(f"Fetching {limit} detections per type for types: {detection_types}")

    # Map detection types to endpoints
    endpoint_map = {
        "rules": "/rules",
        "scheduled_rules": "/scheduled-rules",
        "simple_rules": "/simple-rules",
        "policies": "/policies",
    }

    # Validate all detection types
    invalid_types = [dt for dt in detection_types if dt not in endpoint_map]
    if invalid_types:
        valid_types = ", ".join(endpoint_map.keys())
        return {
            "success": False,
            "message": f"Invalid detection_types {invalid_types}. Valid values are: {valid_types}",
        }

    # For multiple detection types, cursor pagination is not supported
    if len(detection_types) > 1 and cursor:
        return {
            "success": False,
            "message": "Cursor pagination is not supported when querying multiple detection types. Please query one type at a time for pagination.",
        }

    # Validate filtering parameters
    if state and state not in ["enabled", "disabled"]:
        return {
            "success": False,
            "message": "Invalid state value. Must be 'enabled' or 'disabled'.",
        }

    if severity:
        valid_severities = ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
        invalid_severities = [s for s in severity if s not in valid_severities]
        if invalid_severities:
            return {
                "success": False,
                "message": f"Invalid severity values: {invalid_severities}. Valid values are: {', '.join(valid_severities)}",
            }

    if compliance_status and compliance_status not in ["PASS", "FAIL", "ERROR"]:
        return {
            "success": False,
            "message": "Invalid compliance_status value. Must be 'PASS', 'FAIL', or 'ERROR'.",
        }

    # Validate detection-type-specific parameters
    if log_type and not any(dt in ["rules", "simple_rules"] for dt in detection_types):
        return {
            "success": False,
            "message": "log_type parameter is only valid for 'rules' and 'simple_rules' detection types.",
        }

    if resource_type and "policies" not in detection_types:
        return {
            "success": False,
            "message": "resource_type parameter is only valid for 'policies' detection type.",
        }

    if compliance_status and "policies" not in detection_types:
        return {
            "success": False,
            "message": "compliance_status parameter is only valid for 'policies' detection type.",
        }

    # Map detection types to response field names
    field_map = {
        "rules": "rules",
        "scheduled_rules": "scheduled_rules",
        "simple_rules": "simple_rules",
        "policies": "policies",
    }

    try:
        all_results = {}
        has_next_pages = {}
        next_cursors = {}

        async with get_rest_client() as client:
            for detection_type in detection_types:
                # Prepare query parameters
                params = {"limit": limit}
                if cursor and cursor.lower() != "null" and len(detection_types) == 1:
                    params["cursor"] = cursor
                    logger.info(f"Using cursor for pagination: {cursor}")

                # Add common filtering parameters
                if name_contains:
                    params["name-contains"] = name_contains
                if state:
                    params["state"] = state
                if severity:
                    params["severity"] = severity
                if tag:
                    params["tag"] = tag
                if created_by:
                    params["created-by"] = created_by
                if last_modified_by:
                    params["last-modified-by"] = last_modified_by

                # Add detection-type-specific parameters
                if detection_type == "rules":
                    if log_type:
                        params["log-type"] = log_type
                elif detection_type == "simple_rules":
                    if log_type:
                        params["log-type"] = log_type
                elif detection_type == "policies":
                    if resource_type:
                        params["resource-type"] = resource_type
                    if compliance_status:
                        params["compliance-status"] = compliance_status
                elif detection_type == "scheduled_rules":
                    # scheduled_rules has scheduled-query parameter, but we don't expose it yet
                    pass

                result, _ = await client.get(
                    endpoint_map[detection_type], params=params
                )

                # Extract detections and pagination info
                detections = result.get("results", [])
                next_cursor = result.get("next")

                # Store results for this detection type
                all_results[detection_type] = detections
                next_cursors[detection_type] = next_cursor
                has_next_pages[detection_type] = bool(next_cursor)

        # Process results for each detection type
        response_data = {"success": True}

        for detection_type in detection_types:
            detections = all_results[detection_type]

            # Keep only specific fields for each detection to limit the amount of data returned
            if detection_type == "policies":
                filtered_metadata = [
                    {
                        "id": item["id"],
                        "description": item.get("description"),
                        "displayName": item.get("displayName"),
                        "enabled": item.get("enabled", False),
                        "severity": item.get("severity"),
                        "resourceTypes": item.get("resourceTypes", []),
                        "tags": item.get("tags", []),
                        "reports": item.get("reports", {}),
                        "managed": item.get("managed", False),
                        "createdAt": item.get("createdAt"),
                        "lastModified": item.get("lastModified"),
                    }
                    for item in detections
                ]
            elif detection_type == "scheduled_rules":
                filtered_metadata = [
                    {
                        "id": item["id"],
                        "description": item.get("description"),
                        "displayName": item.get("displayName"),
                        "enabled": item.get("enabled", False),
                        "severity": item.get("severity"),
                        "scheduledQueries": item.get("scheduledQueries", []),
                        "tags": item.get("tags", []),
                        "reports": item.get("reports", {}),
                        "managed": item.get("managed", False),
                        "createdAt": item.get("createdAt"),
                        "lastModified": item.get("lastModified"),
                    }
                    for item in detections
                ]
            else:  # rules and simple_rules
                filtered_metadata = [
                    {
                        "id": item["id"],
                        "description": item.get("description"),
                        "displayName": item.get("displayName"),
                        "enabled": item.get("enabled"),
                        "severity": item.get("severity"),
                        "logTypes": item.get("logTypes"),
                        "tags": item.get("tags"),
                        "reports": item.get("reports", {}),
                        "managed": item.get("managed"),
                        "createdAt": item.get("createdAt"),
                        "lastModified": item.get("lastModified"),
                    }
                    for item in detections
                ]

            # Add to response
            response_data[field_map[detection_type]] = filtered_metadata
            response_data[f"total_{field_map[detection_type]}"] = len(filtered_metadata)

            # Add pagination info (only for single detection type queries)
            if len(detection_types) == 1:
                response_data["has_next_page"] = has_next_pages[detection_type]
                response_data["next_cursor"] = next_cursors[detection_type]
            else:
                response_data[f"{detection_type}_has_next_page"] = has_next_pages[
                    detection_type
                ]
                response_data[f"{detection_type}_next_cursor"] = next_cursors[
                    detection_type
                ]

        # Add overall summary for multi-type queries
        if len(detection_types) > 1:
            total_detections = sum(len(all_results[dt]) for dt in detection_types)
            response_data["total_all_detections"] = total_detections
            response_data["detection_types_queried"] = detection_types

        logger.info(f"Successfully retrieved detections for types: {detection_types}")
        return response_data
    except Exception as e:
        logger.error(f"Failed to list detection types {detection_types}: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to list detection types {detection_types}: {str(e)}",
        }


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.RULE_READ, Permission.POLICY_READ),
    }
)
async def get_detection(
    detection_id: Annotated[str, "The ID of the detection to fetch"],
    detection_type: Annotated[List[str], "Type of detection to fetch"] = ["rules"],
) -> Dict[str, Any]:
    """Get detailed information about a Panther detection, including the detection body and tests.

    Args:
        detection_id: The ID of the detection to fetch
        detection_type: Type of detection to fetch. Valid options: ["rules"], ["scheduled_rules"], ["simple_rules"], ["policies"]. For single ID lookups, typically specify one type.
    """
    if not detection_type:
        return {
            "success": False,
            "message": "At least one detection type must be specified.",
        }

    logger.info(f"Fetching details for ID {detection_id} in types: {detection_type}")

    # Map detection types to endpoints
    endpoint_map = {
        "rules": f"/rules/{detection_id}",
        "scheduled_rules": f"/scheduled-rules/{detection_id}",
        "simple_rules": f"/simple-rules/{detection_id}",
        "policies": f"/policies/{detection_id}",
    }

    # Validate all detection types
    invalid_types = [dt for dt in detection_type if dt not in endpoint_map]
    if invalid_types:
        return {
            "success": False,
            "message": f"Invalid detection_types {invalid_types}. Valid values are: rules, scheduled_rules, simple_rules, policies",
        }

    # Map detection types to response field names
    field_map = {
        "rules": "rule",
        "scheduled_rules": "scheduled_rule",
        "simple_rules": "simple_rule",
        "policies": "policy",
    }

    try:
        found_results = {}
        not_found_types = []

        async with get_rest_client() as client:
            for dt in detection_type:
                # Allow 404 as a valid response to handle not found case
                result, status = await client.get(
                    endpoint_map[dt], expected_codes=[200, 404]
                )

                if status == 404:
                    not_found_types.append(dt)
                    logger.warning(f"No {dt.rstrip('s')} found with ID: {detection_id}")
                else:
                    found_results[dt] = result
                    logger.info(
                        f"Successfully retrieved {dt} details for ID: {detection_id}"
                    )

        # If we found results in any detection type, return success
        if found_results:
            response = {"success": True}

            # Add results for each found type
            for dt, result in found_results.items():
                response[field_map[dt]] = result

            # Add info about not found types if any
            if not_found_types:
                response["not_found_in_types"] = not_found_types
                response["found_in_types"] = list(found_results.keys())

            return response
        else:
            # Not found in any of the specified detection types
            return {
                "success": False,
                "message": f"No detection found with ID {detection_id} in any of the specified types: {detection_type}",
            }
    except Exception as e:
        logger.error(
            f"Failed to get detection details for types {detection_type}: {str(e)}"
        )
        return {
            "success": False,
            "message": f"Failed to get detection details for types {detection_type}: {str(e)}",
        }


@mcp_tool(
    annotations={
        "permissions": any_perms(Permission.RULE_MODIFY, Permission.POLICY_MODIFY),
    }
)
async def disable_detection(
    detection_id: Annotated[str, "The ID of the detection to disable"],
    detection_type: Annotated[str, "Type of detection to disable"] = "rules",
) -> Dict[str, Any]:
    """Disable a Panther detection by setting enabled to false.

    Args:
        detection_id: The ID of the detection to disable
        detection_type: Type of detection to disable. Valid options: "rules", "scheduled_rules", "simple_rules", "policies"

    Returns:
        Dict containing:
        - success: Boolean indicating if the update was successful
        - [detection_type]: Updated detection information if successful
        - message: Error message if unsuccessful
    """
    logger.info(f"Disabling {detection_type} with ID: {detection_id}")

    # Map detection types to endpoints
    endpoint_map = {
        "rules": f"/rules/{detection_id}",
        "scheduled_rules": f"/scheduled-rules/{detection_id}",
        "simple_rules": f"/simple-rules/{detection_id}",
        "policies": f"/policies/{detection_id}",
    }

    # Map detection types to response field names
    field_map = {
        "rules": "rule",
        "scheduled_rules": "scheduled_rule",
        "simple_rules": "simple_rule",
        "policies": "policy",
    }

    # Validate detection type
    if detection_type not in endpoint_map:
        valid_types = ", ".join(endpoint_map.keys())
        return {
            "success": False,
            "message": f"Invalid detection_type '{detection_type}'. Valid values are: {valid_types}",
        }

    try:
        async with get_rest_client() as client:
            # First get the current detection to preserve other fields
            current_detection, status = await client.get(
                endpoint_map[detection_type], expected_codes=[200, 404]
            )

            if status == 404:
                return {
                    "success": False,
                    "message": f"{detection_type.replace('_', ' ').title()} with ID {detection_id} not found",
                }

            # Update only the enabled field
            current_detection["enabled"] = False

            # Skip tests for simple disable operation (mainly for rules)
            params = (
                {"run-tests-first": "false"}
                if detection_type in ["rules", "scheduled_rules", "simple_rules"]
                else {}
            )

            # Make the update request
            result, _ = await client.put(
                endpoint_map[detection_type], json_data=current_detection, params=params
            )

        logger.info(f"Successfully disabled {detection_type} with ID: {detection_id}")
        return {"success": True, field_map[detection_type]: result}

    except Exception as e:
        logger.error(f"Failed to disable {detection_type}: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to disable {detection_type}: {str(e)}",
        }
