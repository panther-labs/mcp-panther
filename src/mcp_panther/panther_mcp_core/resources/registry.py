"""
Registry for auto-registering MCP resources.

This module provides a decorator-based approach to register MCP resources.
Resources decorated with @mcp_resource will be automatically collected in a registry
and can be registered with the MCP server using register_all_resources().
"""

import logging
from functools import wraps
from typing import Callable, Dict, Optional, Set

logger = logging.getLogger("mcp-panther")

# Registry to store all decorated resources
_resource_registry: Dict[str, Callable] = {}


def mcp_resource(
    uri: str,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    mime_type: Optional[str] = None,
    tags: Optional[Set[str]] = None,
):
    """
    Decorator to mark a function as an MCP resource.

    Functions decorated with this will be automatically registered
    when register_all_resources() is called.

    Args:
        uri: The resource URI to register (e.g., "config://panther")
        name: Optional name for the resource
        description: Optional description of the resource
        mime_type: Optional MIME type for the resource
        tags: Optional set of tags for the resource

    Example:
        @mcp_resource("config://panther", name="Panther Config", description="Panther configuration data")
        def get_panther_config():
            ...
    """

    def decorator(func: Callable) -> Callable:
        # Store metadata on the function
        func._mcp_resource_metadata = {
            "uri": uri,
            "name": name,
            "description": description,
            "mime_type": mime_type,
            "tags": tags,
        }
        _resource_registry[uri] = func

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    return decorator


def register_all_resources(mcp_instance) -> None:
    """
    Register all resources marked with @mcp_resource with the given MCP instance.

    Args:
        mcp_instance: The FastMCP instance to register resources with
    """
    logger.info(f"Registering {len(_resource_registry)} resources with MCP")

    for uri, resource_func in _resource_registry.items():
        logger.debug(f"Registering resource: {uri} -> {resource_func.__name__}")
        # Get resource metadata if it exists
        metadata = getattr(resource_func, "_mcp_resource_metadata", {})

        # Create resource decorator with metadata
        resource_decorator = mcp_instance.resource(
            uri=metadata["uri"],
            name=metadata.get("name"),
            description=metadata.get("description"),
            mime_type=metadata.get("mime_type"),
            tags=metadata.get("tags"),
        )

        # Register the resource
        resource_decorator(resource_func)

    logger.info("All resources registered successfully")


def get_available_resource_paths() -> list[str]:
    """
    Get a list of all registered resource paths.

    Returns:
        A list of the paths of all registered resources
    """
    return sorted(_resource_registry.keys())
