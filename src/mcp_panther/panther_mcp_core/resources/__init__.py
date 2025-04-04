"""
Package for Panther MCP resources.

This package contains all the resource endpoints available for Panther through MCP.
All resource modules are imported here to ensure they are available.
"""

# Define all modules that should be available when importing this package
__all__ = ["config"]

# Import all resource modules to ensure their decorators are processed
from . import config
