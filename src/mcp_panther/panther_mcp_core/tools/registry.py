"""
Registry for auto-registering MCP tools.

This module provides a decorator-based approach to register MCP tools.
Tools decorated with @mcp_tool will be automatically collected in a registry
and can be registered with the MCP server using register_all_tools().
"""

import logging
from functools import wraps
from typing import Any, Callable, Dict, Optional, Set

logger = logging.getLogger("mcp-panther")

# Registry to store all decorated tools
_tool_registry: Set[Callable] = set()


def mcp_tool(
    func: Optional[Callable] = None,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    annotations: Optional[Dict[str, Any]] = None,
) -> Callable:
    """
    Decorator to mark a function as an MCP tool.

    Functions decorated with this will be automatically registered
    when register_all_tools() is called.

    Can be used in two ways:
    1. Direct decoration:
        @mcp_tool
        def my_tool():
            ...

    2. With parameters:
        @mcp_tool(
            name="custom_name",
            description="Custom description",
            annotations={"category": "data_analysis"}
        )
        def my_tool():
            ...

    Args:
        func: The function to decorate
        name: Optional custom name for the tool. If not provided, uses the function name.
        description: Optional description of what the tool does. If not provided, uses the function's docstring.
        annotations: Optional dictionary of additional annotations for the tool.
    """

    def decorator(func: Callable) -> Callable:
        # Store metadata on the function
        func._mcp_tool_metadata = {
            "name": name,
            "description": description,
            "annotations": annotations,
        }
        _tool_registry.add(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    # Handle both @mcp_tool and @mcp_tool(...) cases
    if func is None:
        return decorator
    return decorator(func)


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

        # Get tool metadata if it exists
        metadata = getattr(tool, "_mcp_tool_metadata", {})

        # Create tool decorator with metadata
        tool_decorator = mcp_instance.tool(
            name=metadata.get("name"),
            description=metadata.get("description"),
            annotations=metadata.get("annotations"),
        )

        # Register the tool
        tool_decorator(tool)

    logger.info("All tools registered successfully")


def get_available_tool_names() -> list[str]:
    """
    Get a list of all registered tool names.

    Returns:
        A list of the names of all registered tools
    """
    return sorted([tool.__name__ for tool in _tool_registry])
