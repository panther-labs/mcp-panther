"""
MCP Panther - An MCP server for interacting with Panther Security Platform.
"""


from .server import MCP_SERVER_NAME, mcp



def main():
    """Entry point for the MCP server that delegates to MCP's run method."""
    mcp.run()


__all__ = ["mcp", "main", "MCP_SERVER_NAME"]
