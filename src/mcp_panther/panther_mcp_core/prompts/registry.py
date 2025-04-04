"""
Registry for managing MCP prompts.

This module provides functions for registering prompt templates with the MCP server.
"""

import logging
from typing import Callable, Set

logger = logging.getLogger("mcp-panther")

# Registry to store all prompt functions
_prompt_registry: Set[Callable] = set()


def mcp_prompt(func: Callable) -> Callable:
    """
    Register a function as an MCP prompt template.

    Functions registered with this will be automatically added to the registry
    and can be registered with the MCP server using register_all_prompts().

    Example:
        @mcp_prompt
        def triage_alert(alert_id: str) -> str:
            ...
    """
    _prompt_registry.add(func)

    return func


def register_all_prompts(mcp_instance) -> None:
    """
    Register all prompt templates with the given MCP instance.

    Args:
        mcp_instance: The FastMCP instance to register prompts with
    """
    logger.info(f"Registering {len(_prompt_registry)} prompts with MCP")

    for prompt in _prompt_registry:
        logger.debug(f"Registering prompt: {prompt.__name__}")
        mcp_instance.prompt()(prompt)

    logger.info("All prompts registered successfully")


def get_available_prompt_names() -> list[str]:
    """
    Get a list of all registered prompt names.

    Returns:
        A list of the names of all registered prompts
    """
    return [prompt.__name__ for prompt in _prompt_registry]
