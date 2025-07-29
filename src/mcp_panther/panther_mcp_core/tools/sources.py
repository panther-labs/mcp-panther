"""
Tools for interacting with Panther log sources.
"""

import logging
from typing import Any

from pydantic import Field
from typing_extensions import Annotated

from ..client import _create_panther_client, get_rest_client
from ..permissions import Permission, all_perms
from ..queries import GET_SOURCES_QUERY
from .registry import mcp_tool

logger = logging.getLogger("mcp-panther")


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.RULE_READ),
        "readOnlyHint": True,
    }
)
async def list_log_sources(
    cursor: Annotated[
        str | None,
        Field(description="Optional cursor for pagination from a previous query"),
    ] = None,
    log_types: Annotated[
        list[str],
        Field(
            description="Optional list of log types to filter by",
            examples=[["AWS.CloudTrail", "AWS.S3ServerAccess"]],
        ),
    ] = [],
    is_healthy: Annotated[
        bool,
        Field(
            description="Optional boolean to filter by health status (default: True)"
        ),
    ] = True,
    integration_type: Annotated[
        str | None,
        Field(
            description="Optional integration type to filter by",
            examples=[
                "amazon-eventbridge",
                "amazon-security-lake",
                "aws-cloudwatch-logs",
                "aws-s3",
                "aws-scan",
                "aws-sqs",
                "azure-blob",
                "azure-eventhub",
                "gcp-gcs",
                "gcp-pubsub",
                "http-ingest",
                "log-pulling",
                "profile-pulling",
                "s3-lookuptable",
            ],
        ),
    ] = None,
) -> dict[str, Any]:
    """List log sources from Panther with optional filters."""
    logger.info("Fetching log sources from Panther")

    try:
        client = await _create_panther_client()

        # Prepare input variables
        variables = {"input": {}}

        # Add cursor if provided
        if cursor:
            variables["input"]["cursor"] = cursor
            logger.info(f"Using cursor for pagination: {cursor}")

        logger.debug(f"Query variables: {variables}")

        # Execute the query asynchronously
        async with client as session:
            result = await session.execute(GET_SOURCES_QUERY, variable_values=variables)

        # Log the raw result for debugging
        logger.debug(f"Raw query result: {result}")

        # Process results
        sources_data = result.get("sources", {})
        source_edges = sources_data.get("edges", [])
        page_info = sources_data.get("pageInfo", {})

        # Extract sources from edges
        sources = [edge["node"] for edge in source_edges]

        # Apply post-request filtering
        if is_healthy is not None:
            sources = [
                source for source in sources if source["isHealthy"] == is_healthy
            ]
            logger.info(f"Filtered by health status: {is_healthy}")

        if log_types:
            sources = [
                source
                for source in sources
                if any(log_type in source["logTypes"] for log_type in log_types)
            ]
            logger.info(f"Filtered by log types: {log_types}")

        if integration_type:
            sources = [
                source
                for source in sources
                if source["integrationType"] == integration_type
            ]
            logger.info(f"Filtered by integration type: {integration_type}")

        logger.info(f"Successfully retrieved {len(sources)} log sources")

        # Format the response
        return {
            "success": True,
            "sources": sources,
            "total_sources": len(sources),
            "has_next_page": page_info.get("hasNextPage", False),
            "has_previous_page": page_info.get("hasPreviousPage", False),
            "end_cursor": page_info.get("endCursor"),
            "start_cursor": page_info.get("startCursor"),
        }
    except Exception as e:
        logger.error(f"Failed to fetch log sources: {str(e)}")
        return {"success": False, "message": f"Failed to fetch log sources: {str(e)}"}


@mcp_tool(
    annotations={
        "permissions": all_perms(Permission.LOG_SOURCE_READ),
        "readOnlyHint": True,
    }
)
async def get_http_log_source(
    source_id: Annotated[
        str,
        Field(
            description="The ID of the HTTP log source to fetch",
            examples=["http-source-123", "webhook-collector-456"],
        ),
    ],
) -> dict[str, Any]:
    """Get detailed information about a specific HTTP log source by ID.

    HTTP log sources are used to collect logs via HTTP endpoints/webhooks.
    This tool provides detailed configuration information for troubleshooting
    and monitoring HTTP log source integrations.

    Args:
        source_id: The ID of the HTTP log source to retrieve

    Returns:
        Dict containing:
        - success: Boolean indicating if the query was successful
        - source: HTTP log source information if successful, containing:
            - integrationId: The source ID
            - integrationLabel: The source name/label
            - logTypes: List of log types this source handles
            - logStreamType: Stream type (Auto, JSON, JsonArray, etc.)
            - logStreamTypeOptions: Additional stream type configuration
            - authMethod: Authentication method (None, Bearer, Basic, etc.)
            - authBearerToken: Bearer token if using Bearer auth
            - authUsername: Username if using Basic auth
            - authPassword: Password if using Basic auth
            - authHeaderKey: Header key for HMAC/SharedSecret auth
            - authSecretValue: Secret value for HMAC/SharedSecret auth
            - authHmacAlg: HMAC algorithm if using HMAC auth
        - message: Error message if unsuccessful
    """
    logger.info(f"Fetching HTTP log source: {source_id}")

    try:
        # Execute the REST API call
        async with get_rest_client() as client:
            response_data, status_code = await client.get(
                f"/log-sources/http/{source_id}"
            )

        logger.info(f"Successfully retrieved HTTP log source: {source_id}")

        # Format the response
        return {
            "success": True,
            "source": response_data,
        }
    except Exception as e:
        logger.error(f"Failed to fetch HTTP log source: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch HTTP log source: {str(e)}",
        }
