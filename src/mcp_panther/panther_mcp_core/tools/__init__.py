"""
Package for Panther MCP tools.

This package contains all the tool functions available for Panther through MCP.
All tool modules are imported here to ensure their decorators are processed.
"""

# Define all modules that should be available when importing this package
__all__ = [
    "alerts",
    "detections",
    "data_lake",
    "data_models",
    "sources",
    "metrics",
    "users",
    "roles",
    "globals",
    "schemas",
    "helpers",
    "permissions",
]

# Import all tool modules to ensure decorators are processed
from . import (
    alerts,
    data_lake,
    data_models,
    detections,
    globals,
    helpers,
    metrics,
    permissions,
    roles,
    schemas,
    sources,
    users,
)
