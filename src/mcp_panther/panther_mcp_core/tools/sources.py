"""
Tools for interacting with Panther log sources.
"""

import logging
from typing import Any

from pydantic import BeforeValidator, Field
from typing_extensions import Annotated

from ..client import _execute_query, get_rest_client
from ..permissions import Permission, all_perms
from ..queries import GET_SOURCES_QUERY
from ..validators import _validate_auth_method, _validate_log_stream_type
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
        # Prepare input variables
        variables = {"input": {}}

        # Add cursor if provided
        if cursor:
            variables["input"]["cursor"] = cursor
            logger.info(f"Using cursor for pagination: {cursor}")

        logger.debug(f"Query variables: {variables}")

        # Execute the query using shared client
        result = await _execute_query(GET_SOURCES_QUERY, variables)

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
        "permissions": all_perms(Permission.LOG_SOURCE_MODIFY),
        "destructiveHint": False,
        "idempotentHint": False,
    }
)
async def create_http_log_source(
    integration_label: Annotated[
        str,
        Field(
            description="The name/label for the HTTP log source",
            min_length=1,
            examples=["My Webhook Source", "SIEM Forwarder"],
        ),
    ],
    log_types: Annotated[
        list[str],
        Field(
            description="List of log types this source will handle",
            min_length=1,
            examples=[["Custom.WebhookData"], ["AWS.CloudTrail", "Custom.AppLogs"]],
        ),
    ],
    log_stream_type: Annotated[
        str,
        BeforeValidator(_validate_log_stream_type),
        Field(
            description="The log stream type for parsing incoming data",
            examples=["Auto", "JSON", "JsonArray", "Lines", "CloudWatchLogs", "XML"],
        ),
    ],
    auth_method: Annotated[
        str,
        BeforeValidator(_validate_auth_method),
        Field(
            description="The authentication method for the HTTP source",
            examples=["None", "Bearer", "Basic", "HMAC", "SharedSecret"],
        ),
    ],
    auth_bearer_token: Annotated[
        str | None,
        Field(
            description="Bearer token value. Required when auth_method is 'Bearer'",
        ),
    ] = None,
    auth_username: Annotated[
        str | None,
        Field(
            description="Username for Basic auth. Required when auth_method is 'Basic'",
        ),
    ] = None,
    auth_password: Annotated[
        str | None,
        Field(
            description="Password for Basic auth. Required when auth_method is 'Basic'",
        ),
    ] = None,
    auth_header_key: Annotated[
        str | None,
        Field(
            description="Header key for HMAC or SharedSecret auth. Required when auth_method is 'HMAC' or 'SharedSecret'",
        ),
    ] = None,
    auth_secret_value: Annotated[
        str | None,
        Field(
            description="Secret value for HMAC or SharedSecret auth. Required when auth_method is 'HMAC' or 'SharedSecret'",
        ),
    ] = None,
    auth_hmac_alg: Annotated[
        str | None,
        Field(
            description="HMAC algorithm. Required when auth_method is 'HMAC'",
            examples=["sha256", "sha512"],
        ),
    ] = None,
    json_array_envelope_field: Annotated[
        str | None,
        Field(
            description="Path to the array value to extract elements from. Only applicable when log_stream_type is 'JsonArray'. Leave empty if the input JSON is an array itself",
        ),
    ] = None,
) -> dict[str, Any]:
    """Create a new HTTP log source in Panther for ingesting logs via HTTP endpoint/webhook.

    This tool onboards a new HTTP log source that can receive logs via HTTP POST requests.
    After creation, Panther will provide an integration ID that can be used to send logs
    to the source's HTTP endpoint.

    Authentication parameters are conditionally required based on the auth_method:
    - None: No additional auth parameters needed
    - Bearer: Requires auth_bearer_token
    - Basic: Requires auth_username and auth_password
    - HMAC: Requires auth_header_key, auth_secret_value, and auth_hmac_alg
    - SharedSecret: Requires auth_header_key and auth_secret_value
    """
    logger.info(f"Creating HTTP log source: {integration_label}")

    try:
        # Build the request payload with required fields
        payload: dict[str, Any] = {
            "integrationLabel": integration_label,
            "logTypes": log_types,
            "logStreamType": log_stream_type,
            "authMethod": auth_method,
        }

        # Add auth-specific fields based on method
        if auth_method == "Bearer":
            if not auth_bearer_token:
                return {
                    "success": False,
                    "message": "auth_bearer_token is required when auth_method is 'Bearer'",
                }
            payload["authBearerToken"] = auth_bearer_token

        elif auth_method == "Basic":
            if not auth_username or not auth_password:
                return {
                    "success": False,
                    "message": "auth_username and auth_password are required when auth_method is 'Basic'",
                }
            payload["authUsername"] = auth_username
            payload["authPassword"] = auth_password

        elif auth_method == "HMAC":
            if not auth_header_key or not auth_secret_value or not auth_hmac_alg:
                return {
                    "success": False,
                    "message": "auth_header_key, auth_secret_value, and auth_hmac_alg are required when auth_method is 'HMAC'",
                }
            payload["authHeaderKey"] = auth_header_key
            payload["authSecretValue"] = auth_secret_value
            payload["authHmacAlg"] = auth_hmac_alg

        elif auth_method == "SharedSecret":
            if not auth_header_key or not auth_secret_value:
                return {
                    "success": False,
                    "message": "auth_header_key and auth_secret_value are required when auth_method is 'SharedSecret'",
                }
            payload["authHeaderKey"] = auth_header_key
            payload["authSecretValue"] = auth_secret_value

        # Add optional log stream type options
        if json_array_envelope_field is not None:
            payload["logStreamTypeOptions"] = {
                "jsonArrayEnvelopeField": json_array_envelope_field,
            }

        # Execute the REST API call
        async with get_rest_client() as client:
            response_data, status_code = await client.post(
                "/log-sources/http",
                json_data=payload,
                expected_codes=[201],
            )

        logger.info(
            f"Successfully created HTTP log source: {response_data.get('integrationId', 'unknown')}"
        )

        return {
            "success": True,
            "source": response_data,
        }
    except Exception as e:
        logger.error(f"Failed to create HTTP log source: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to create HTTP log source: {str(e)}",
        }


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
