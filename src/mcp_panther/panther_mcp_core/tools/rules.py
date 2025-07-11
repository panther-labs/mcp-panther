"""
Tools for interacting with Panther rules.
"""

import logging
from typing import Any, Dict, List

from typing_extensions import Annotated

from ..client import get_rest_client
from ..permissions import Permission, all_perms
from .registry import mcp_tool

logger = logging.getLogger("mcp-panther")


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.RULE_READ, Permission.POLICY_READ),
    }
)
async def list_detections(
    detection_types: Annotated[
        List[str],
        "Types of detections to list"
    ] = ["rules"],
    cursor: Annotated[
        str | None, "Optional cursor for pagination from a previous query"
    ] = None,
    limit: Annotated[int, "Maximum number of results to return"] = 100,
) -> Dict[str, Any]:
    """List detections from your Panther instance with support for different detection types.

    Args:
        detection_types: Types of detections to list. Valid options: ["rules"], ["scheduled_rules"], ["simple_rules"], ["policies"]
        cursor: Optional cursor for pagination from a previous query
        limit: Maximum number of results to return (default: 100)
    """
    # For now, we only support single detection type queries
    if len(detection_types) != 1:
        return {
            "success": False,
            "message": "Currently only single detection type queries are supported. Please specify exactly one detection type.",
        }
    
    detection_type = detection_types[0]
    logger.info(f"Fetching {limit} {detection_type} from Panther")

    # Map detection types to endpoints
    endpoint_map = {
        "rules": "/rules",
        "scheduled_rules": "/scheduled-rules",
        "simple_rules": "/simple-rules",
        "policies": "/policies",
    }
    
    # Validate detection_type
    if detection_type not in endpoint_map:
        valid_types = ", ".join(endpoint_map.keys())
        return {
            "success": False,
            "message": f"Invalid detection_type '{detection_type}'. Valid values are: {valid_types}",
        }

    # Map detection types to response field names
    field_map = {
        "rules": "rules",
        "scheduled_rules": "scheduled_rules",
        "simple_rules": "simple_rules",
        "policies": "policies",
    }

    try:
        # Prepare query parameters
        params = {"limit": limit}
        if cursor and cursor.lower() != "null":  # Only add cursor if it's not null
            params["cursor"] = cursor
            logger.info(f"Using cursor for pagination: {cursor}")

        async with get_rest_client() as client:
            result, _ = await client.get(endpoint_map[detection_type], params=params)

        # Extract detections and pagination info
        detections = result.get("results", [])
        next_cursor = result.get("next")

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

        logger.info(f"Successfully retrieved {len(filtered_metadata)} {detection_type}")

        return {
            "success": True,
            field_map[detection_type]: filtered_metadata,
            f"total_{field_map[detection_type]}": len(filtered_metadata),
            "has_next_page": bool(next_cursor),
            "next_cursor": next_cursor,
        }
    except Exception as e:
        logger.error(f"Failed to list {detection_type}: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to list {detection_type}: {str(e)}",
        }


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.RULE_READ, Permission.POLICY_READ),
    }
)
async def get_detection_by_id(
    detection_id: Annotated[str, "The ID of the detection to fetch"],
    detection_type: Annotated[
        List[str],
        "Type of detection to fetch"
    ] = ["rules"],
) -> Dict[str, Any]:
    """Get detailed information about a Panther detection, including the detection body and tests.

    Args:
        detection_id: The ID of the detection to fetch
        detection_type: Type of detection to fetch. Valid options: ["rules"], ["scheduled_rules"], ["simple_rules"], ["policies"]
    """
    # For now, we only support single detection type queries
    if len(detection_type) != 1:
        return {
            "success": False,
            "message": "Currently only single detection type queries are supported. Please specify exactly one detection type.",
        }
    
    detection_type_str = detection_type[0]
    logger.info(f"Fetching {detection_type_str} details for ID: {detection_id}")

    # Map detection types to endpoints
    endpoint_map = {
        "rules": f"/rules/{detection_id}",
        "scheduled_rules": f"/scheduled-rules/{detection_id}",
        "simple_rules": f"/simple-rules/{detection_id}",
        "policies": f"/policies/{detection_id}",
    }
    
    # Validate detection_type
    if detection_type_str not in endpoint_map:
        return {
            "success": False,
            "message": f"Invalid detection_type '{detection_type_str}'. Valid values are: rules, scheduled_rules, simple_rules, policies",
        }

    # Map detection types to response field names
    field_map = {
        "rules": "rule",
        "scheduled_rules": "scheduled_rule",
        "simple_rules": "simple_rule",
        "policies": "policy",
    }

    try:
        async with get_rest_client() as client:
            # Allow 404 as a valid response to handle not found case
            result, status = await client.get(
                endpoint_map[detection_type_str], expected_codes=[200, 404]
            )

            if status == 404:
                logger.warning(
                    f"No {detection_type_str.rstrip('s')} found with ID: {detection_id}"
                )
                return {
                    "success": False,
                    "message": f"No {detection_type_str.rstrip('s')} found with ID: {detection_id}",
                }

        logger.info(
            f"Successfully retrieved {detection_type_str} details for ID: {detection_id}"
        )
        return {"success": True, field_map[detection_type_str]: result}
    except Exception as e:
        logger.error(f"Failed to get {detection_type_str} details: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to get {detection_type_str} details: {str(e)}",
        }


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.RULE_MODIFY),
    }
)
async def disable_rule(rule_id: str) -> Dict[str, Any]:
    """Disable a Panther rule by setting enabled to false.

    Args:
        rule_id: The ID of the rule to disable

    Returns:
        Dict containing:
        - success: Boolean indicating if the update was successful
        - rule: Updated rule information if successful
        - message: Error message if unsuccessful
    """
    logger.info(f"Disabling rule with ID: {rule_id}")

    try:
        async with get_rest_client() as client:
            # First get the current rule to preserve other fields
            current_rule, status = await client.get(
                f"/rules/{rule_id}", expected_codes=[200, 404]
            )

            if status == 404:
                return {
                    "success": False,
                    "message": f"Rule with ID {rule_id} not found",
                }

            # Update only the enabled field
            current_rule["enabled"] = False

            # Skip tests for simple disable operation
            params = {"run-tests-first": "false"}

            # Make the update request
            result, _ = await client.put(
                f"/rules/{rule_id}", json_data=current_rule, params=params
            )

        logger.info(f"Successfully disabled rule with ID: {rule_id}")
        return {"success": True, "rule": result}

    except Exception as e:
        logger.error(f"Failed to disable rule: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to disable rule: {str(e)}",
        }
