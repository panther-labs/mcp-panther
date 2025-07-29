"""
Tools for interacting with Panther data-models.
"""

import logging
from typing import Annotated, Any

from pydantic import Field

from ..client import get_rest_client
from ..permissions import Permission, all_perms
from .registry import mcp_tool

logger = logging.getLogger("mcp-panther")


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.RULE_READ),
        "readOnlyHint": True,
    }
)
async def list_data_models(
    cursor: Annotated[
        str | None,
        Field(description="Optional cursor for pagination from a previous query"),
    ] = None,
    limit: Annotated[
        int,
        Field(
            description="Maximum number of results to return (1-1000)",
            examples=[100, 25, 50],
            ge=1,
            le=1000,
        ),
    ] = 100,
) -> dict[str, Any]:
    """List all data models from your Panther instance. Data models are used only in Panther's Python rules to map log type schema fields to a unified data model. They may also contain custom mappings for fields that are not part of the log type schema.

    Returns paginated list of data models with metadata including mappings and log types.
    """
    logger.info(f"Fetching {limit} data models from Panther")

    try:
        # Prepare query parameters
        params = {"limit": limit}
        if cursor and cursor.lower() != "null":  # Only add cursor if it's not null
            params["cursor"] = cursor
            logger.info(f"Using cursor for pagination: {cursor}")

        async with get_rest_client() as client:
            result, _ = await client.get("/data-models", params=params)

        # Extract data models and pagination info
        data_models = result.get("results", [])
        next_cursor = result.get("next")

        # Keep only specific fields for each data model to limit the amount of data returned
        filtered_data_models_metadata = [
            {
                "id": data_model["id"],
                "description": data_model.get("description"),
                "displayName": data_model.get("displayName"),
                "enabled": data_model.get("enabled"),
                "logTypes": data_model.get("logTypes"),
                "mappings": data_model.get("mappings"),
                "managed": data_model.get("managed"),
                "createdAt": data_model.get("createdAt"),
                "lastModified": data_model.get("lastModified"),
            }
            for data_model in data_models
        ]

        logger.info(
            f"Successfully retrieved {len(filtered_data_models_metadata)} data models"
        )

        return {
            "success": True,
            "data_models": filtered_data_models_metadata,
            "total_data_models": len(filtered_data_models_metadata),
            "has_next_page": bool(next_cursor),
            "next_cursor": next_cursor,
        }
    except Exception as e:
        logger.error(f"Failed to list data models: {str(e)}")
        return {"success": False, "message": f"Failed to list data models: {str(e)}"}


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.RULE_READ),
        "readOnlyHint": True,
    }
)
async def get_data_model(
    data_model_id: Annotated[
        str,
        Field(
            description="The ID of the data model to fetch",
            examples=["MyDataModel", "AWS_CloudTrail", "StandardUser"],
        ),
    ],
) -> dict[str, Any]:
    """Get detailed information about a Panther data model, including the mappings and body

    Returns complete data model information including Python body code and UDM mappings.
    """
    logger.info(f"Fetching data model details for data model ID: {data_model_id}")

    try:
        async with get_rest_client() as client:
            # Allow 404 as a valid response to handle not found case
            result, status = await client.get(
                f"/data-models/{data_model_id}", expected_codes=[200, 404]
            )

            if status == 404:
                logger.warning(f"No data model found with ID: {data_model_id}")
                return {
                    "success": False,
                    "message": f"No data model found with ID: {data_model_id}",
                }

        logger.info(
            f"Successfully retrieved data model details for data model ID: {data_model_id}"
        )
        return {"success": True, "data_model": result}
    except Exception as e:
        logger.error(f"Failed to get data model details: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to get data model details: {str(e)}",
        }
