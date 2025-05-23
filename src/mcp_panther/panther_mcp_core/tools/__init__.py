"""
Package for Panther MCP tools.

This package contains all the tool functions available for Panther through MCP.
All tool modules are imported here to ensure their decorators are processed.
"""

# Define all modules that should be available when importing this package
__all__ = [
    "alerts",
    "rules",
    "data_lake",
    "sources",
    "metrics",
    "users",
    "schemas",
    "helpers",
    "permissions",
]

# Import all tool modules to ensure decorators are processed
from . import (
    alerts,
    data_lake,
    helpers,
    metrics,
    permissions,
    rules,
    schemas,
    sources,
    users,
)
