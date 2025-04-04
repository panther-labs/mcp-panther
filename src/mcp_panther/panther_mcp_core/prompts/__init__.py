"""
Package for Panther MCP prompts.

This package contains all the prompt templates available for Panther through MCP.
All prompt modules are imported here to ensure they are available.
"""

# Define all modules that should be available when importing this package
__all__ = ["alert_triage"]

# Import all prompt modules to ensure their decorators are processed
from . import alert_triage
