"""
Tools for interacting with Panther rules.
"""

import logging
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..client import get_rest_client
from .registry import mcp_tool

logger = logging.getLogger("mcp-panther")


@mcp_tool
async def list_rules(cursor: str = None, limit: int = 100) -> Dict[str, Any]:
    """List all rules from your Panther instance.

    Args:
        cursor: Optional cursor for pagination from a previous query
        limit: Optional maximum number of results to return (default: 100)
    """
    logger.info(f"Fetching {limit} rules from Panther")

    try:
        # Prepare query parameters
        params = {"limit": limit}
        if cursor and cursor.lower() != "null":  # Only add cursor if it's not null
            params["cursor"] = cursor
            logger.info(f"Using cursor for pagination: {cursor}")

        async with get_rest_client() as client:
            result, _ = await client.get("/rules", params=params)

        # Extract rules and pagination info
        rules = result.get("results", [])
        next_cursor = result.get("next")

        # Keep only specific fields for each rule to limit the amount of data returned
        filtered_rules_metadata = [
            {
                "id": rule["id"],
                "description": rule.get("description"),
                "displayName": rule.get("displayName"),
                "enabled": rule.get("enabled"),
                "severity": rule.get("severity"),
                "logTypes": rule.get("logTypes"),
                "tags": rule.get("tags"),
                "reports": rule.get("reports", {}),
                "managed": rule.get("managed"),
                "createdAt": rule.get("createdAt"),
                "lastModified": rule.get("lastModified"),
            }
            for rule in rules
        ]

        logger.info(f"Successfully retrieved {len(filtered_rules_metadata)} rules")

        return {
            "success": True,
            "rules": filtered_rules_metadata,
            "total_rules": len(filtered_rules_metadata),
            "has_next_page": bool(next_cursor),
            "next_cursor": next_cursor,
        }
    except Exception as e:
        logger.error(f"Failed to list rules: {str(e)}")
        return {"success": False, "message": f"Failed to list rules: {str(e)}"}


@mcp_tool
async def get_rule_by_id(rule_id: str) -> Dict[str, Any]:
    """Get detailed information about a Panther rule, including the rule body and tests

    Args:
        rule_id: The ID of the rule to fetch
    """
    logger.info(f"Fetching rule details for rule ID: {rule_id}")

    try:
        async with get_rest_client() as client:
            # Allow 404 as a valid response to handle not found case
            result, status = await client.get(
                f"/rules/{rule_id}", expected_codes=[200, 404]
            )

            if status == 404:
                logger.warning(f"No rule found with ID: {rule_id}")
                return {
                    "success": False,
                    "message": f"No rule found with ID: {rule_id}",
                }

        logger.info(f"Successfully retrieved rule details for rule ID: {rule_id}")
        return {"success": True, "rule": result}
    except Exception as e:
        logger.error(f"Failed to get rule details: {str(e)}")
        return {"success": False, "message": f"Failed to get rule details: {str(e)}"}


class UnitTest(BaseModel):
    """Model for a Panther rule unit test."""

    name: str = Field(description="A descriptive name of the test case")
    resource: str = Field(
        default="{}",
        description="The test event data (either a log event or cloud resource) as a JSON string",
    )
    expectedResult: bool = Field(description="The expected result of the test")  # noqa: N815
    mocks: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Optional mocks for the test"
    )


class RuleCreate(BaseModel):
    """Model for creating a new Panther rule."""

    model_config = ConfigDict(
        populate_by_name=True,  # Allow both camelCase and snake_case
        json_schema_extra={
            "example": {
                "id": "AWS.S3.Bucket.PublicAccess",
                "body": "def rule(event):\n    return True",
                "severity": "HIGH",
                "description": "Detects when an S3 bucket is made publicly accessible",
                "displayName": "S3 Bucket Public Access",
                "logTypes": ["AWS.S3"],
                "tests": [
                    {
                        "name": "Public Access Enabled",
                        "resource": '{"bucketName": "test-bucket", "publicAccessBlock": false}',
                        "expectedResult": True,
                    },
                    {
                        "name": "Public Access Disabled",
                        "resource": '{"bucketName": "test-bucket", "publicAccessBlock": true}',
                        "expectedResult": False,
                    },
                ],
            }
        },
    )

    id: str = Field(description="Unique identifier for the rule")
    body: str = Field(description="Python code that implements the rule logic")
    severity: Literal["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(
        description="Alert severity level"
    )
    description: str = Field(
        description="Description for what the rule is meant to detect"
    )
    displayName: str = Field(description="Human-readable name for the rule")  # noqa: N815
    enabled: bool = Field(default=True, description="Whether the rule is active")
    logTypes: List[str] = Field(  # noqa: N815
        description="The list of log types this rule applies to (e.g. ['AWS.CloudTrail', 'AWS.GuardDuty'])"
    )
    dedupPeriodMinutes: int = Field(  # noqa: N815
        default=60,
        ge=1,
        le=1440,
        description="The time window for alert deduplication in minutes based on the title or dedup key",
    )
    threshold: int = Field(
        default=1,
        ge=1,
        description="The minimum number of events required to trigger an alert",
    )
    runbook: Optional[str] = Field(
        default=None,
        description="Instructions for handling alerts (read by the Panther AI triage agent)",
    )
    tags: Optional[List[str]] = Field(
        default=None, description="A list of tags for categorization"
    )
    summaryAttributes: Optional[List[str]] = Field(  # noqa: N815
        default=None,
        description="A list of column names for summarizing alerts (e.g. ['p_any_ip_addresses', 'p_any_user_ids'])",
    )
    inlineFilters: Optional[str] = Field(  # noqa: N815
        default=None, description="A YAML filter for the rule"
    )
    reports: Optional[Dict[str, List[str]]] = Field(
        default=None, description="A mapping of compliance report names to destinations"
    )
    tests: Optional[List[UnitTest]] = Field(
        default=None,
        description="A list of test cases to validate the rule's logic (create one True and one False test)",
    )


@mcp_tool
async def create_rule(
    rule: RuleCreate,
    run_tests_first: bool = True,
) -> Dict[str, Any]:
    """Create a new Panther rule. First, think about the type of behavior you want to detect, then query the data lake for sample logs to use as examples for your rule. Read a similar rule with recent alerts and use it as a template.

    The Panther Python streaming rule body requires a `rule(event)` function that analyzes each log event and returns `True` to trigger an alert or `False` otherwise, with event data accessed safely using `event.get("field", default_value)` for top-level fields and `event.deep_get("parent", "child", "field", default_value)` for nested structures. Supplementary functions like `title(event)` (required), `severity(event)`, `alert_context(event)`, and `destinations(event)` (all optional) enhance alerts by providing descriptive titles, dynamic severity levels, contextual instructions for runbooks, and custom destination routing based on event data. All rules must handle missing fields gracefully, respect the 15-second execution time limit, and follow the stateless execution model where each event is processed independently. Panther provides standardized fields with the `p_` prefix (like `p_log_type`, `p_event_time`, `p_any_ip_addresses`) across all log types, and rules should leverage these normalized fields for consistency while focusing on a single, clear detection pattern per rule.

    Args:
        rule: The rule data to create
        run_tests_first: Whether to run tests before saving (default: True)

    Returns:
        Dict containing:
        - success: Boolean indicating if the creation was successful
        - rule: Created rule information if successful
        - message: Error message if unsuccessful
    """
    logger.info(f"Creating new rule with ID: {rule.id}")

    try:
        # Convert rule model to dict, excluding None values
        rule_data = rule.model_dump(exclude_none=True)

        # Prepare query parameters
        params = {"run-tests-first": str(run_tests_first).lower()}

        async with get_rest_client() as client:
            # Allow 409 as a valid response to handle conflict case
            result, status = await client.post(
                "/rules", json_data=rule_data, params=params, expected_codes=[200, 409]
            )

            if status == 409:
                return {
                    "success": False,
                    "message": "Rule with this ID already exists",
                }

        logger.info(f"Successfully created rule with ID: {rule.id}")
        return {"success": True, "rule": result}

    except Exception as e:
        logger.error(f"Failed to create rule: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to create rule: {str(e)}",
        }


@mcp_tool
async def put_rule(
    rule_id: str,
    body: str,
    severity: str,
    description: str = None,
    display_name: str = None,
    enabled: bool = None,
    log_types: List[str] = None,
    dedup_period_minutes: int = None,
    threshold: int = None,
    runbook: str = None,
    tags: List[str] = None,
    summary_attributes: List[str] = None,
    inline_filters: str = None,
    reports: dict = None,
    tests: List[dict] = None,
    run_tests_first: bool = True,
) -> Dict[str, Any]:
    """Update an existing Panther rule or create a new one if it doesn't exist.

    Args:
        rule_id: Unique identifier for the rule
        body: Python code that implements the rule logic
        severity: Alert severity level (INFO, LOW, MEDIUM, HIGH, CRITICAL)
        description: Optional description of what the rule does
        display_name: Optional display name for the rule
        enabled: Optional boolean to enable/disable the rule
        log_types: Optional list of log types this rule applies to
        dedup_period_minutes: Optional time window for alert deduplication
        threshold: Optional number of events required to trigger alert
        runbook: Optional documentation on how to handle alerts
        tags: Optional list of tags for categorization
        summary_attributes: Optional list of fields to summarize in alerts
        inline_filters: Optional YAML filter for the rule
        reports: Optional mapping of report names to destinations
        tests: Optional list of unit tests for the rule
        run_tests_first: Whether to run tests before saving (default: True)

    Returns:
        Dict containing:
        - success: Boolean indicating if the update was successful
        - rule: Updated rule information if successful
        - message: Error message if unsuccessful
    """
    logger.info(f"Updating rule with ID: {rule_id}")

    try:
        # Validate severity
        valid_severities = ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
        if severity not in valid_severities:
            raise ValueError(f"Severity must be one of {valid_severities}")

        # Prepare rule data
        rule_data = {
            "id": rule_id,
            "body": body,
            "severity": severity,
        }

        # Add optional fields if provided
        if enabled is not None:
            rule_data["enabled"] = enabled
        if description:
            rule_data["description"] = description
        if display_name:
            rule_data["displayName"] = display_name
        if log_types:
            rule_data["logTypes"] = log_types
        if dedup_period_minutes:
            rule_data["dedupPeriodMinutes"] = dedup_period_minutes
        if threshold:
            rule_data["threshold"] = threshold
        if runbook:
            rule_data["runbook"] = runbook
        if tags:
            rule_data["tags"] = tags
        if summary_attributes:
            rule_data["summaryAttributes"] = summary_attributes
        if inline_filters:
            rule_data["inlineFilters"] = inline_filters
        if reports:
            rule_data["reports"] = reports
        if tests:
            rule_data["tests"] = tests

        # Prepare query parameters
        params = {"run-tests-first": str(run_tests_first).lower()}

        async with get_rest_client() as client:
            result, _ = await client.put(
                f"/rules/{rule_id}", json_data=rule_data, params=params
            )

        logger.info(f"Successfully updated rule with ID: {rule_id}")
        return {"success": True, "rule": result}

    except Exception as e:
        logger.error(f"Failed to update rule: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to update rule: {str(e)}",
        }


@mcp_tool
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


@mcp_tool
async def list_scheduled_rules(cursor: str = None, limit: int = 100) -> Dict[str, Any]:
    """List all scheduled rules from Panther with optional pagination

    Args:
        cursor: Optional cursor for pagination from a previous query
        limit: Optional maximum number of results to return (default: 100)
    """
    logger.info("Fetching scheduled rules from Panther")

    try:
        # Prepare query parameters
        params = {"limit": limit}
        if cursor and cursor.lower() != "null":  # Only add cursor if it's not null
            params["cursor"] = cursor
            logger.info(f"Using cursor for pagination: {cursor}")

        async with get_rest_client() as client:
            result, _ = await client.get("/scheduled-rules", params=params)

        # Extract rules and pagination info
        scheduled_rules = result.get("results", [])
        next_cursor = result.get("next")

        # Keep only specific fields for each rule to limit the amount of data returned
        filtered_rules_metadata = [
            {
                "id": rule["id"],
                "description": rule.get("description"),
                "displayName": rule.get("displayName"),
                "enabled": rule.get("enabled", False),
                "severity": rule.get("severity"),
                "scheduledQueries": rule.get("scheduledQueries", []),
                "tags": rule.get("tags", []),
                "reports": rule.get("reports", {}),
                "managed": rule.get("managed", False),
                "createdAt": rule.get("createdAt"),
                "lastModified": rule.get("lastModified"),
            }
            for rule in scheduled_rules
        ]

        logger.info(
            f"Successfully retrieved {len(filtered_rules_metadata)} scheduled rules"
        )

        # Format the response
        return {
            "success": True,
            "scheduled_rules": filtered_rules_metadata,
            "total_scheduled_rules": len(filtered_rules_metadata),
            "has_next_page": bool(next_cursor),
            "next_cursor": next_cursor,
        }
    except Exception as e:
        logger.error(f"Failed to fetch scheduled rules: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch scheduled rules: {str(e)}",
        }


@mcp_tool
async def get_scheduled_rule_by_id(rule_id: str) -> Dict[str, Any]:
    """Get detailed information about a Panther scheduled rule by ID including the rule body and tests

    Args:
        rule_id: The ID of the scheduled rule to fetch
    """
    logger.info(f"Fetching scheduled rule details for ID: {rule_id}")

    try:
        async with get_rest_client() as client:
            # Allow 404 as a valid response to handle not found case
            result, status = await client.get(
                f"/scheduled-rules/{rule_id}", expected_codes=[200, 404]
            )

            if status == 404:
                logger.warning(f"No scheduled rule found with ID: {rule_id}")
                return {
                    "success": False,
                    "message": f"No scheduled rule found with ID: {rule_id}",
                }

        logger.info(f"Successfully retrieved scheduled rule details for ID: {rule_id}")

        # Format the response
        return {"success": True, "scheduled_rule": result}
    except Exception as e:
        logger.error(f"Failed to fetch scheduled rule details: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch scheduled rule details: {str(e)}",
        }


@mcp_tool
async def list_simple_rules(cursor: str = None, limit: int = 100) -> Dict[str, Any]:
    """List all simple rules from Panther with optional pagination

    Args:
        cursor: Optional cursor for pagination from a previous query
        limit: Optional maximum number of results to return (default: 100)
    """
    logger.info("Fetching simple rules from Panther")

    try:
        # Prepare query parameters
        params = {"limit": limit}
        if cursor and cursor.lower() != "null":  # Only add cursor if it's not null
            params["cursor"] = cursor
            logger.info(f"Using cursor for pagination: {cursor}")

        async with get_rest_client() as client:
            result, _ = await client.get("/simple-rules", params=params)

        # Extract rules and pagination info
        simple_rules = result.get("results", [])
        next_cursor = result.get("next")

        # Keep only specific fields for each rule to limit the amount of data returned
        filtered_rules_metadata = [
            {
                "id": rule["id"],
                "description": rule.get("description"),
                "displayName": rule.get("displayName"),
                "enabled": rule.get("enabled", False),
                "severity": rule.get("severity"),
                "logTypes": rule.get("logTypes", []),
                "tags": rule.get("tags", []),
                "reports": rule.get("reports", {}),
                "managed": rule.get("managed", False),
                "createdAt": rule.get("createdAt"),
                "lastModified": rule.get("lastModified"),
            }
            for rule in simple_rules
        ]

        logger.info(
            f"Successfully retrieved {len(filtered_rules_metadata)} simple rules"
        )

        # Format the response
        return {
            "success": True,
            "simple_rules": filtered_rules_metadata,
            "total_simple_rules": len(filtered_rules_metadata),
            "has_next_page": bool(next_cursor),
            "next_cursor": next_cursor,
        }
    except Exception as e:
        logger.error(f"Failed to fetch simple rules: {str(e)}")
        return {"success": False, "message": f"Failed to fetch simple rules: {str(e)}"}


@mcp_tool
async def get_simple_rule_by_id(rule_id: str) -> Dict[str, Any]:
    """Get detailed information about a Panther simple rule by ID including the rule body and tests

    Args:
        rule_id: The ID of the simple rule to fetch
    """
    logger.info(f"Fetching simple rule details for ID: {rule_id}")

    try:
        async with get_rest_client() as client:
            # Allow 404 as a valid response to handle not found case
            result, status = await client.get(
                f"/simple-rules/{rule_id}", expected_codes=[200, 404]
            )

            if status == 404:
                logger.warning(f"No simple rule found with ID: {rule_id}")
                return {
                    "success": False,
                    "message": f"No simple rule found with ID: {rule_id}",
                }

        logger.info(f"Successfully retrieved simple rule details for ID: {rule_id}")

        # Format the response
        return {"success": True, "simple_rule": result}
    except Exception as e:
        logger.error(f"Failed to fetch simple rule details: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch simple rule details: {str(e)}",
        }
