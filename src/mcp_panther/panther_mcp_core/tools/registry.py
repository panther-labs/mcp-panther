"""
Registry for auto-registering MCP tools.

This module provides a decorator-based approach to register MCP tools.
Tools decorated with @mcp_tool will be automatically collected in a registry
and can be registered with the MCP server using register_all_tools().
"""

import logging
from functools import wraps
from typing import Callable, Set

logger = logging.getLogger("mcp-panther")

# Registry to store all decorated tools
_tool_registry: Set[Callable] = set()


def mcp_tool(func: Callable) -> Callable:
    """
    Decorator to mark a function as an MCP tool.

    Functions decorated with this will be automatically registered
    when register_all_tools() is called.

    Example:
        @mcp_tool
        async def list_alerts(...):
            ...
    """
    _tool_registry.add(func)

    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def register_all_tools(mcp_instance) -> None:
    """
    Register all tools marked with @mcp_tool with the given MCP instance.

    Args:
        mcp_instance: The FastMCP instance to register tools with
    """
    logger.info(f"Registering {len(_tool_registry)} tools with MCP")

    # Sort tools by name
    sorted_funcs = sorted(_tool_registry, key=lambda f: f.__name__)
    for tool in sorted_funcs:
        logger.debug(f"Registering tool: {tool.__name__}")
        mcp_instance.tool()(tool)

    logger.info("All tools registered successfully")


def get_available_tool_names() -> list[str]:
    """
    Get a list of all registered tool names.

    Returns:
        A list of the names of all registered tools
    """
    return sorted([tool.__name__ for tool in _tool_registry])
