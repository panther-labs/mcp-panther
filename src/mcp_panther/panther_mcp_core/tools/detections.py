"""
Tools for interacting with Panther rules.
"""

import logging
from typing import Any

from pydantic import Field
from typing_extensions import Annotated

from ..client import get_rest_client
from ..permissions import Permission, all_perms, any_perms
from .registry import mcp_tool

logger = logging.getLogger("mcp-panther")

# Detection type constants
DETECTION_TYPES = {
    "rules": "/rules",
    "scheduled_rules": "/scheduled-rules",
    "simple_rules": "/simple-rules",
    "policies": "/policies",
}

# Response field mappings
LIST_FIELD_MAP = {
    "rules": "rules",
    "scheduled_rules": "scheduled_rules",
    "simple_rules": "simple_rules",
    "policies": "policies",
}

SINGULAR_FIELD_MAP = {
    "rules": "rule",
    "scheduled_rules": "scheduled_rule",
    "simple_rules": "simple_rule",
    "policies": "policy",
}

# Valid parameter values
VALID_SEVERITIES = ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
VALID_STATES = ["enabled", "disabled"]
VALID_COMPLIANCE_STATUSES = ["PASS", "FAIL", "ERROR"]


def validate_detection_types(detection_types: list[str]) -> dict[str, Any] | None:
    """Validate detection types and return error dict if invalid, None if valid."""
    if not detection_types:
        return {
            "success": False,
            "message": "At least one detection type must be specified.",
        }

    invalid_types = [dt for dt in detection_types if dt not in DETECTION_TYPES]
    if invalid_types:
        valid_types = ", ".join(DETECTION_TYPES.keys())
        return {
            "success": False,
            "message": f"Invalid detection_types {invalid_types}. Valid values are: {valid_types}",
        }
    return None


def get_endpoint_for_detection(
    detection_type: str, detection_id: str | None = None
) -> str:
    """Get the API endpoint for a detection type, optionally with an ID."""
    base_endpoint = DETECTION_TYPES[detection_type]
    return f"{base_endpoint}/{detection_id}" if detection_id else base_endpoint


def build_detection_params(
    limit: int,
    cursor: str | None,
    detection_types: list[str],
    name_contains: str | None,
    state: str | None,
    severity: list[str] | None,
    tag: list[str] | None,
    created_by: str | None,
    last_modified_by: str | None,
    log_type: list[str] | None,
    resource_type: list[str] | None,
    compliance_status: str | None,
    detection_type: str,
) -> dict[str, Any]:
    """Build query parameters for detection API calls."""
    params = {"limit": limit}

    # Add cursor for single detection type queries only
    if cursor and len(detection_types) == 1:
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
    if detection_type in ["rules", "simple_rules"] and log_type:
        params["log-type"] = log_type
    elif detection_type == "policies":
        if resource_type:
            params["resource-type"] = resource_type
        if compliance_status:
            params["compliance-status"] = compliance_status

    return params


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.RULE_READ, Permission.POLICY_READ),
        "readOnlyHint": True,
    }
)
async def list_detections(
    detection_types: Annotated[
        list[str],
        Field(
            description="One or more detection types - rules, scheduled_rules, simple_rules, or policies.",
            examples=[
                ["rules", "simple_rules", "scheduled_rules"],
                ["policies"],
            ],
        ),
    ] = ["rules"],
    cursor: Annotated[
        str | None,
        Field(
            description="Optional cursor for pagination from a previous query (only supported for single detection type)"
        ),
    ] = None,
    limit: Annotated[
        int,
        Field(
            description="Maximum number of results to return per detection type",
            default=100,
            ge=1,
            le=1000,
        ),
    ] = 100,
    name_contains: Annotated[
        str | None, Field(description="Substring search by name (case-insensitive)")
    ] = None,
    state: Annotated[
        str,
        Field(
            description="Filter by state - 'enabled' or 'disabled'", default="enabled"
        ),
    ] = "",
    severity: Annotated[
        list[str],
        Field(
            description="Filter by severity levels - INFO, LOW, MEDIUM, HIGH, or CRITICAL.",
            examples=[
                ["MEDIUM", "HIGH", "CRITICAL"],
                ["INFO", "LOW"],
            ],
        ),
    ] = [],
    tag: Annotated[
        list[str],
        Field(
            description="A case-insensitive list of tags to filter by.",
            examples=[["Initial Access", "Persistence"]],
        ),
    ] = [],
    log_type: Annotated[
        list[str],
        Field(
            description="A list of log types to filter by (applies to rules and simple-rules only).",
            examples=[["AWS.CloudTrail", "GCP.AuditLog"]],
        ),
    ] = [],
    resource_type: Annotated[
        list[str],
        Field(
            description="Filter by resource types (applies to policies only) - list of resource type names",
            examples=[["AWS.S3.Bucket", "AWS.EC2.SecurityGroup"]],
        ),
    ] = [],
    compliance_status: Annotated[
        str | None,
        Field(
            description="Filter by compliance status (applies to policies only) - 'PASS', 'FAIL', or 'ERROR'"
        ),
    ] = None,
    created_by: Annotated[
        str | None, Field(description="Filter by creator user ID or actor ID")
    ] = None,
    last_modified_by: Annotated[
        str | None, Field(description="Filter by last modifier user ID or actor ID")
    ] = None,
    output_ids: Annotated[
        list[str],
        Field(
            description="Client-side filter by destination output IDs. Filters results after fetching from API to include only detections with at least one matching outputID.",
            examples=[["destination-id-123"], ["prod-slack", "prod-pagerduty"]],
        ),
    ] = [],
) -> dict[str, Any]:
    """List detections from your Panther instance with support for multiple detection types and filtering.

    Note: The output_ids filter is applied client-side after fetching all results from the API,
    as the Panther REST API does not support server-side filtering by outputID. For more efficient
    API-level filtering, consider using the 'tag' parameter if your detections are tagged by environment.
    """
    # Validate detection types
    validation_error = validate_detection_types(detection_types)
    if validation_error:
        return validation_error

    logger.info(f"Fetching {limit} detections per type for types: {detection_types}")

    # For multiple detection types, cursor pagination is not supported
    if len(detection_types) > 1 and cursor:
        return {
            "success": False,
            "message": "Cursor pagination is not supported when querying multiple detection types. Please query one type at a time for pagination.",
        }

    # Validate filtering parameters
    if state and state not in VALID_STATES:
        return {
            "success": False,
            "message": f"Invalid state value. Must be one of: {', '.join(VALID_STATES)}",
        }

    if severity:
        invalid_severities = [s for s in severity if s not in VALID_SEVERITIES]
        if invalid_severities:
            return {
                "success": False,
                "message": f"Invalid severity values: {invalid_severities}. Valid values are: {', '.join(VALID_SEVERITIES)}",
            }

    if compliance_status and compliance_status not in VALID_COMPLIANCE_STATUSES:
        return {
            "success": False,
            "message": f"Invalid compliance_status value. Must be one of: {', '.join(VALID_COMPLIANCE_STATUSES)}",
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

    # Use the centralized field mapping
    field_map = LIST_FIELD_MAP

    try:
        all_results = {}
        has_next_pages = {}
        next_cursors = {}

        async with get_rest_client() as client:
            for detection_type in detection_types:
                # Build query parameters using helper function
                params = build_detection_params(
                    limit,
                    cursor,
                    detection_types,
                    name_contains,
                    state,
                    severity,
                    tag,
                    created_by,
                    last_modified_by,
                    log_type,
                    resource_type,
                    compliance_status,
                    detection_type,
                )

                result, _ = await client.get(
                    get_endpoint_for_detection(detection_type), params=params
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
                        "outputIDs": item.get("outputIDs", []),
                        "createdBy": item.get("createdBy"),
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
                        "outputIDs": item.get("outputIDs", []),
                        "threshold": item.get("threshold"),
                        "dedupPeriodMinutes": item.get("dedupPeriodMinutes"),
                        "createdBy": item.get("createdBy"),
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
                        "outputIDs": item.get("outputIDs", []),
                        "threshold": item.get("threshold"),
                        "dedupPeriodMinutes": item.get("dedupPeriodMinutes"),
                        "createdBy": item.get("createdBy"),
                        "createdAt": item.get("createdAt"),
                        "lastModified": item.get("lastModified"),
                    }
                    for item in detections
                ]

            # Apply client-side output_ids filtering if requested
            if output_ids:
                filtered_metadata = [
                    item
                    for item in filtered_metadata
                    if any(
                        output_id in item.get("outputIDs", [])
                        for output_id in output_ids
                    )
                ]
                logger.info(
                    f"Applied client-side output_ids filter for {detection_type}: {len(filtered_metadata)} results matched"
                )

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
        "readOnlyHint": True,
    }
)
async def get_detection(
    detection_id: Annotated[
        str,
        Field(
            description="The ID of the detection to fetch",
            examples=["AWS.Suspicious.S3.Activity", "GCP.K8S.Privileged.Pod.Created"],
        ),
    ],
    detection_type: Annotated[
        list[str],
        Field(
            description="One or more detection types - rules, scheduled_rules, simple_rules, or policies.",
            examples=[
                ["rules", "simple_rules", "scheduled_rules"],
                ["policies"],
            ],
        ),
    ] = ["rules"],
) -> dict[str, Any]:
    """Get detailed information about a Panther detection, including the detection body and tests."""
    # Validate detection types
    validation_error = validate_detection_types(detection_type)
    if validation_error:
        return validation_error

    logger.info(f"Fetching details for ID {detection_id} in types: {detection_type}")

    # Use centralized field mapping
    field_map = SINGULAR_FIELD_MAP

    try:
        found_results = {}
        not_found_types = []

        async with get_rest_client() as client:
            for dt in detection_type:
                # Allow 404 as a valid response to handle not found case
                result, status = await client.get(
                    get_endpoint_for_detection(dt, detection_id),
                    expected_codes=[200, 404],
                )

                if status == 404:
                    not_found_types.append(dt)
                    # Use proper singular form from mapping instead of naive string manipulation
                    singular_form = SINGULAR_FIELD_MAP[dt].replace("_", " ")
                    logger.warning(f"No {singular_form} found with ID: {detection_id}")
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
        "destructiveHint": True,
        "idempotentHint": True,
    }
)
async def disable_detection(
    detection_id: Annotated[
        str,
        Field(
            description="The ID of the detection to disable",
            examples=["AWS.Suspicious.S3.Activity", "GCP.K8S.Privileged.Pod.Created"],
        ),
    ],
    detection_type: Annotated[
        str,
        Field(
            description="Type of detection to disable. Valid options: rules, scheduled_rules, simple_rules, or policies.",
            examples=["rules", "scheduled_rules", "simple_rules", "policies"],
        ),
    ] = "rules",
) -> dict[str, Any]:
    """Disable a Panther detection by setting enabled to false."""
    logger.info(f"Disabling {detection_type} with ID: {detection_id}")

    # Validate detection type
    validation_error = validate_detection_types([detection_type])
    if validation_error:
        return validation_error

    # Use centralized field mapping
    field_map = SINGULAR_FIELD_MAP
    endpoint = get_endpoint_for_detection(detection_type, detection_id)

    try:
        async with get_rest_client() as client:
            # First get the current detection to preserve other fields
            current_detection, status = await client.get(
                endpoint, expected_codes=[200, 404]
            )

            if status == 404:
                return {
                    "success": False,
                    "message": f"{detection_type.replace('_', ' ').title()} with ID {detection_id} not found",
                }

            # Disable the detection by setting enabled to False
            # This modifies the API response object which is then sent back in the PUT request
            current_detection["enabled"] = False

            # Skip tests for simple disable operation (mainly for rules)
            params = (
                {"run-tests-first": "false"}
                if detection_type in ["rules", "scheduled_rules", "simple_rules"]
                else {}
            )

            # Make the update request
            result, _ = await client.put(
                endpoint, json_data=current_detection, params=params
            )

        logger.info(f"Successfully disabled {detection_type} with ID: {detection_id}")
        return {"success": True, field_map[detection_type]: result}

    except Exception as e:
        logger.error(f"Failed to disable {detection_type}: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to disable {detection_type}: {str(e)}",
        }
