"""
Tools for interacting with Panther rules.
"""

import logging
from typing import Any, Dict

from ..client import get_rest_client
from ..permissions import Permission, all_perms
from .registry import mcp_tool

logger = logging.getLogger("mcp-panther")


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.RULE_READ),
    }
)
async def list_rules(cursor: str | None = None, limit: int = 100) -> Dict[str, Any]:
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


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.RULE_READ),
    }
)
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


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.RULE_READ),
    }
)
async def list_scheduled_rules(
    cursor: str | None = None, limit: int = 100
) -> Dict[str, Any]:
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


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.RULE_READ),
    }
)
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


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.RULE_READ),
    }
)
async def list_simple_rules(
    cursor: str | None = None, limit: int = 100
) -> Dict[str, Any]:
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


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.RULE_READ),
    }
)
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


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.POLICY_READ),
    }
)
async def list_policies(cursor: str | None = None, limit: int = 100) -> Dict[str, Any]:
    """List all policies from Panther with optional pagination

    Args:
        cursor: Optional cursor for pagination from a previous query
        limit: Optional maximum number of results to return (default: 100)
    """
    logger.info("Fetching policies from Panther")

    try:
        # Prepare query parameters
        params = {"limit": limit}
        if cursor and cursor.lower() != "null":  # Only add cursor if it's not null
            params["cursor"] = cursor
            logger.info(f"Using cursor for pagination: {cursor}")

        async with get_rest_client() as client:
            result, _ = await client.get("/policies", params=params)

        # Extract policies and pagination info
        policies = result.get("results", [])
        next_cursor = result.get("next")

        # Keep only specific fields for each policy to limit the amount of data returned
        filtered_policies_metadata = [
            {
                "id": policy["id"],
                "description": policy.get("description"),
                "displayName": policy.get("displayName"),
                "enabled": policy.get("enabled", False),
                "severity": policy.get("severity"),
                "resourceTypes": policy.get("resourceTypes", []),
                "tags": policy.get("tags", []),
                "reports": policy.get("reports", {}),
                "managed": policy.get("managed", False),
                "createdAt": policy.get("createdAt"),
                "lastModified": policy.get("lastModified"),
            }
            for policy in policies
        ]

        logger.info(
            f"Successfully retrieved {len(filtered_policies_metadata)} policies"
        )

        # Format the response
        return {
            "success": True,
            "policies": filtered_policies_metadata,
            "total_policies": len(filtered_policies_metadata),
            "has_next_page": bool(next_cursor),
            "next_cursor": next_cursor,
        }
    except Exception as e:
        logger.error(f"Failed to fetch policies: {str(e)}")
        return {"success": False, "message": f"Failed to fetch policies: {str(e)}"}


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.POLICY_READ),
    }
)
async def get_policy_by_id(policy_id: str) -> Dict[str, Any]:
    """Get detailed information about a Panther policy by ID including the policy body and tests

    Args:
        policy_id: The ID of the policy to fetch
    """
    logger.info(f"Fetching policy details for ID: {policy_id}")

    try:
        async with get_rest_client() as client:
            # Allow 404 as a valid response to handle not found case
            result, status = await client.get(
                f"/policies/{policy_id}", expected_codes=[200, 404]
            )

            if status == 404:
                logger.warning(f"No policy found with ID: {policy_id}")
                return {
                    "success": False,
                    "message": f"No policy found with ID: {policy_id}",
                }

        logger.info(f"Successfully retrieved policy details for ID: {policy_id}")

        # Format the response
        return {"success": True, "policy": result}
    except Exception as e:
        logger.error(f"Failed to fetch policy details: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch policy details: {str(e)}",
        }


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.RULE_MODIFY),
    }
)
async def put_rule(rule_id: str, rule: Dict[str, Any]) -> Dict[str, Any]:
    # Implementation of put_rule method
    pass
