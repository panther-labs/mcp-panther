"""
Tools for interacting with Panther schemas.
"""

import logging
from typing import Any

from pydantic import Field
from typing_extensions import Annotated

from ..client import _create_panther_client
from ..permissions import Permission, all_perms
from ..queries import GET_SCHEMA_DETAILS_QUERY, LIST_SCHEMAS_QUERY
from .registry import mcp_tool

logger = logging.getLogger("mcp-panther")


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.LOG_SOURCE_READ),
        "readOnlyHint": True,
    }
)
async def list_log_type_schemas(
    contains: Annotated[
        str | None,
        Field(description="Optional filter by name or schema field name"),
    ] = None,
    is_archived: Annotated[
        bool,
        Field(
            description="Filter by archive status (default: False shows non-archived)"
        ),
    ] = False,
    is_in_use: Annotated[
        bool,
        Field(description="Filter for used/active schemas (default: False shows all)"),
    ] = False,
    is_managed: Annotated[
        bool,
        Field(description="Filter for pack-managed schemas (default: False shows all)"),
    ] = False,
) -> dict[str, Any]:
    """List all available log type schemas in Panther. Schemas are transformation instructions that convert raw audit logs
    into structured data for the data lake and real-time Python rules.

    Returns:
        Dict containing:
        - success: Boolean indicating if the query was successful
        - schemas: List of schemas, each containing:
            - name: Schema name (Log Type)
            - description: Schema description
            - revision: Schema revision number
            - isArchived: Whether the schema is archived
            - isManaged: Whether the schema is managed by a pack
            - referenceURL: Optional documentation URL
            - createdAt: Creation timestamp
            - updatedAt: Last update timestamp
        - message: Error message if unsuccessful
    """
    logger.info("Fetching available schemas")

    try:
        client = await _create_panther_client()

        # Prepare input variables, only including non-default values
        input_vars = {}
        if contains is not None:
            input_vars["contains"] = contains
        if is_archived:
            input_vars["isArchived"] = is_archived
        if is_in_use:
            input_vars["isInUse"] = is_in_use
        if is_managed:
            input_vars["isManaged"] = is_managed

        variables = {"input": input_vars}

        # Execute the query asynchronously
        async with client as session:
            result = await session.execute(
                LIST_SCHEMAS_QUERY, variable_values=variables
            )

        # Get schemas data and ensure we have the required structure
        schemas_data = result.get("schemas")
        if not schemas_data:
            return {"success": False, "message": "No schemas data returned from server"}

        edges = schemas_data.get("edges", [])
        schemas = [edge["node"] for edge in edges] if edges else []

        logger.info(f"Successfully retrieved {len(schemas)} schemas")

        # Format the response
        return {
            "success": True,
            "schemas": schemas,
        }

    except Exception as e:
        logger.error(f"Failed to fetch schemas: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch schemas: {str(e)}",
        }


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.RULE_READ),
        "readOnlyHint": True,
    }
)
async def get_log_type_schema_details(
    schema_names: Annotated[
        list[str],
        Field(
            description="List of schema names to get details for (max 5)",
            examples=[["AWS.CloudTrail", "GCP.AuditLog"]],
        ),
    ],
) -> dict[str, Any]:
    """Get detailed information for specific log type schemas, including their full specifications.
    Limited to 5 schemas at a time to prevent response size issues.

    Returns:
        Dict containing:
        - success: Boolean indicating if the query was successful
        - schemas: List of schemas, each containing:
            - name: Schema name (Log Type)
            - description: Schema description
            - spec: Schema specification in YAML/JSON format
            - version: Schema version number
            - revision: Schema revision number
            - isArchived: Whether the schema is archived
            - isManaged: Whether the schema is managed by a pack
            - isFieldDiscoveryEnabled: Whether automatic field discovery is enabled
            - referenceURL: Optional documentation URL
            - discoveredSpec: The schema discovered spec
            - createdAt: Creation timestamp
            - updatedAt: Last update timestamp
        - message: Error message if unsuccessful
    """
    if not schema_names:
        return {"success": False, "message": "No schema names provided"}

    if len(schema_names) > 5:
        return {
            "success": False,
            "message": "Maximum of 5 schema names allowed per request",
        }

    logger.info(f"Fetching detailed schema information for: {', '.join(schema_names)}")

    try:
        client = await _create_panther_client()
        all_schemas = []

        # Query each schema individually to ensure we get exact matches
        for name in schema_names:
            variables = {"name": name}  # Pass single name as string

            async with client as session:
                result = await session.execute(
                    GET_SCHEMA_DETAILS_QUERY, variable_values=variables
                )

            schemas_data = result.get("schemas")
            if not schemas_data:
                logger.warning(f"No schema data found for {name}")
                continue

            edges = schemas_data.get("edges", [])
            # The query now returns exact matches, so we can use all results
            matching_schemas = [edge["node"] for edge in edges]

            if matching_schemas:
                all_schemas.extend(matching_schemas)
            else:
                logger.warning(f"No match found for schema {name}")

        if not all_schemas:
            return {"success": False, "message": "No matching schemas found"}

        logger.info(f"Successfully retrieved {len(all_schemas)} schemas")

        return {
            "success": True,
            "schemas": all_schemas,
        }

    except Exception as e:
        logger.error(f"Failed to fetch schema details: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch schema details: {str(e)}",
        }
