"""
Registry for managing MCP prompts.

This module provides functions for registering prompt templates with the MCP server.
"""

import logging
from functools import wraps
from typing import Callable, Optional, Set

logger = logging.getLogger("mcp-panther")

# Registry to store all prompt functions
_prompt_registry: Set[Callable] = set()


def mcp_prompt(
    func: Optional[Callable] = None,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[Set[str]] = None,
) -> Callable:
    """
    Register a function as an MCP prompt template.

    Functions registered with this will be automatically added to the registry
    and can be registered with the MCP server using register_all_prompts().

    Can be used in two ways:
    1. Direct decoration:
        @mcp_prompt
        def triage_alert(alert_id: str) -> str:
            ...

    2. With parameters:
        @mcp_prompt(
            name="Custom Triage",
            description="Custom alert triage prompt",
            tags={"triage", "alerts"}
        )
        def triage_alert(alert_id: str) -> str:
            ...

    Args:
        func: The function to decorate
        name: Optional name for the prompt
        description: Optional description of the prompt
        tags: Optional set of tags for the prompt
    """

    def decorator(func: Callable) -> Callable:
        # Store metadata on the function
        func._mcp_prompt_metadata = {
            "name": name,
            "description": description,
            "tags": tags,
        }
        _prompt_registry.add(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    # Handle both @mcp_prompt and @mcp_prompt(...) cases
    if func is None:
        return decorator
    return decorator(func)


def register_all_prompts(mcp_instance) -> None:
    """
    Register all prompt templates with the given MCP instance.

    Args:
        mcp_instance: The FastMCP instance to register prompts with
    """
    logger.info(f"Registering {len(_prompt_registry)} prompts with MCP")

    for prompt in _prompt_registry:
        logger.debug(f"Registering prompt: {prompt.__name__}")

        # Get prompt metadata if it exists
        metadata = getattr(prompt, "_mcp_prompt_metadata", {})

        # Create prompt decorator with metadata
        prompt_decorator = mcp_instance.prompt(
            name=metadata.get("name"),
            description=metadata.get("description"),
            tags=metadata.get("tags"),
        )

        # Register the prompt
        prompt_decorator(prompt)

    logger.info("All prompts registered successfully")


def get_available_prompt_names() -> list[str]:
    """
    Get a list of all registered prompt names.

    Returns:
        A list of the names of all registered prompts
    """
    return sorted([prompt.__name__ for prompt in _prompt_registry])
