"""
Tools for interacting with Panther rules.
"""

import logging
import aiohttp
from typing import Dict, Any, List

from ..client import get_panther_api_key, PANTHER_REST_API_URL
from .registry import mcp_tool

logger = logging.getLogger("mcp-panther")


@mcp_tool
async def list_rules(cursor: str = None, limit: int = 100) -> Dict[str, Any]:
    """List all rules from Panther with optional pagination

    Args:
        cursor: Optional cursor for pagination from a previous query
        limit: Optional maximum number of results to return (default: 100)
    """
    logger.info("Fetching rules from Panther")

    try:
        # Prepare headers
        headers = {
            "X-API-Key": get_panther_api_key(),
            "Content-Type": "application/json",
        }

        # Prepare query parameters
        params = {"limit": limit}
        if cursor and cursor.lower() != "null":  # Only add cursor if it's not null
            params["cursor"] = cursor
            logger.info(f"Using cursor for pagination: {cursor}")

        # Make the request
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{PANTHER_REST_API_URL}/rules", headers=headers, params=params
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(
                        f"Failed to fetch rules (HTTP {response.status}): {error_text}"
                    )

                result = await response.json()

        # Extract rules and pagination info
        rules = result.get("results", [])
        next_cursor = result.get("next")

        logger.info(f"Successfully retrieved {len(rules)} rules")

        # Format the response
        return {
            "success": True,
            "rules": rules,
            "total_rules": len(rules),
            "has_next_page": bool(next_cursor),
            "next_cursor": next_cursor,
        }
    except Exception as e:
        logger.error(f"Failed to fetch rules: {str(e)}")
        return {"success": False, "message": f"Failed to fetch rules: {str(e)}"}


@mcp_tool
async def get_rule_by_id(rule_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific Panther rule by ID

    Args:
        rule_id: The ID of the rule to fetch
    """
    logger.info(f"Fetching rule details for ID: {rule_id}")

    try:
        # Prepare headers
        headers = {
            "X-API-Key": get_panther_api_key(),
            "Content-Type": "application/json",
        }

        # Make the request
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{PANTHER_REST_API_URL}/rules/{rule_id}", headers=headers
            ) as response:
                if response.status == 404:
                    logger.warning(f"No rule found with ID: {rule_id}")
                    return {
                        "success": False,
                        "message": f"No rule found with ID: {rule_id}",
                    }
                elif response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Failed to fetch rule details: {error_text}")

                rule_data = await response.json()

        logger.info(f"Successfully retrieved rule details for ID: {rule_id}")

        # Format the response
        return {"success": True, "rule": rule_data}
    except Exception as e:
        logger.error(f"Failed to fetch rule details: {str(e)}")
        return {"success": False, "message": f"Failed to fetch rule details: {str(e)}"}


@mcp_tool
async def create_rule(
    rule_id: str,
    body: str,
    severity: str,
    description: str = None,
    display_name: str = None,
    enabled: bool = True,
    log_types: List[str] = None,
    dedup_period_minutes: int = 60,
    threshold: int = 1,
    runbook: str = None,
    tags: List[str] = None,
    summary_attributes: List[str] = None,
    inline_filters: str = None,
    reports: dict = None,
    tests: List[dict] = None,
    run_tests_first: bool = True,
) -> Dict[str, Any]:
    """Create a new Panther rule.

    Args:
        rule_id: Unique identifier for the rule
        body: Python code that implements the rule logic
        severity: Alert severity level (INFO, LOW, MEDIUM, HIGH, CRITICAL)
        description: Optional description of what the rule does
        display_name: Optional display name for the rule
        enabled: Whether the rule is active (default: True)
        log_types: Optional list of log types this rule applies to
        dedup_period_minutes: Time window for alert deduplication (default: 60)
        threshold: Number of events required to trigger alert (default: 1)
        runbook: Optional documentation on how to handle alerts
        tags: Optional list of tags for categorization
        summary_attributes: Optional list of fields to summarize in alerts
        inline_filters: Optional YAML filter for the rule
        reports: Optional mapping of report names to destinations
        tests: Optional list of unit tests for the rule
        run_tests_first: Whether to run tests before saving (default: True)

    Returns:
        Dict containing:
        - success: Boolean indicating if the creation was successful
        - rule: Created rule information if successful
        - message: Error message if unsuccessful
    """
    logger.info(f"Creating new rule with ID: {rule_id}")

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
            "enabled": enabled,
            "dedupPeriodMinutes": dedup_period_minutes,
            "threshold": threshold,
        }

        # Add optional fields if provided
        if description:
            rule_data["description"] = description
        if display_name:
            rule_data["displayName"] = display_name
        if log_types:
            rule_data["logTypes"] = log_types
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

        # Prepare headers and query parameters
        headers = {
            "X-API-Key": get_panther_api_key(),
            "Content-Type": "application/json",
        }
        params = {"run-tests-first": str(run_tests_first).lower()}

        # Make the request
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{PANTHER_REST_API_URL}/rules",
                headers=headers,
                params=params,
                json=rule_data,
            ) as response:
                if response.status == 409:
                    return {
                        "success": False,
                        "message": "Rule with this ID already exists",
                    }
                elif response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Failed to create rule: {error_text}")

                result = await response.json()

        logger.info(f"Successfully created rule with ID: {rule_id}")

        return {
            "success": True,
            "rule": result,
        }

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

        # Prepare headers and query parameters
        headers = {
            "X-API-Key": get_panther_api_key(),
            "Content-Type": "application/json",
        }
        params = {"run-tests-first": str(run_tests_first).lower()}

        # Make the request
        async with aiohttp.ClientSession() as session:
            async with session.put(
                f"{PANTHER_REST_API_URL}/rules/{rule_id}",
                headers=headers,
                params=params,
                json=rule_data,
            ) as response:
                if response.status not in [200, 201]:
                    error_text = await response.text()
                    raise Exception(f"Failed to update rule: {error_text}")

                result = await response.json()

        logger.info(f"Successfully updated rule with ID: {rule_id}")

        return {
            "success": True,
            "rule": result,
        }

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
        # First get the current rule to preserve other fields
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{PANTHER_REST_API_URL}/rules/{rule_id}",
                headers={"X-API-Key": get_panther_api_key()},
            ) as response:
                if response.status == 404:
                    return {
                        "success": False,
                        "message": f"Rule with ID {rule_id} not found",
                    }
                elif response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Failed to fetch rule: {error_text}")

                rule_data = await response.json()

        # Update only the enabled field
        rule_data["enabled"] = False

        # Prepare headers and query parameters
        headers = {
            "X-API-Key": get_panther_api_key(),
            "Content-Type": "application/json",
        }
        params = {"run-tests-first": "false"}  # Skip tests for simple disable

        # Make the update request
        async with aiohttp.ClientSession() as session:
            async with session.put(
                f"{PANTHER_REST_API_URL}/rules/{rule_id}",
                headers=headers,
                params=params,
                json=rule_data,
            ) as response:
                if response.status not in [200, 201]:
                    error_text = await response.text()
                    raise Exception(f"Failed to disable rule: {error_text}")

                result = await response.json()

        logger.info(f"Successfully disabled rule with ID: {rule_id}")

        return {
            "success": True,
            "rule": result,
        }

    except Exception as e:
        logger.error(f"Failed to disable rule: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to disable rule: {str(e)}",
        }
