"""
Registry for auto-registering MCP resources.

This module provides a decorator-based approach to register MCP resources.
Resources decorated with @mcp_resource will be automatically collected in a registry
and can be registered with the MCP server using register_all_resources().
"""

import logging
from functools import wraps
from typing import Callable, Dict

logger = logging.getLogger("mcp-panther")

# Registry to store all decorated resources
_resource_registry: Dict[str, Callable] = {}


def mcp_resource(resource_path: str):
    """
    Decorator to mark a function as an MCP resource.

    Functions decorated with this will be automatically registered
    when register_all_resources() is called.

    Args:
        resource_path: The resource path to register (e.g., "config://panther")

    Example:
        @mcp_resource("config://panther")
        def get_panther_config(...):
            ...
    """

    def decorator(func: Callable) -> Callable:
        _resource_registry[resource_path] = func

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

    for resource_path, resource_func in _resource_registry.items():
        logger.debug(
            f"Registering resource: {resource_path} -> {resource_func.__name__}"
        )
        mcp_instance.resource(resource_path)(resource_func)

    logger.info("All resources registered successfully")


def get_available_resource_paths() -> list[str]:
    """
    Get a list of all registered resource paths.

    Returns:
        A list of the paths of all registered resources
    """
    return sorted(_resource_registry.keys())
