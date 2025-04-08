"""
MCP Panther - An MCP server for interacting with Panther Security Platform.
"""
from .server import mcp, MCP_SERVER_NAME

def main():
    """Entry point for the MCP server that delegates to MCP's run method."""
    mcp.run()

__all__ = ["mcp", "main", "MCP_SERVER_NAME"]