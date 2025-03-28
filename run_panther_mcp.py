#!/usr/bin/env python3
"""
Runner script for the Panther MCP server.
"""
import uvicorn

if __name__ == "__main__":
    # Run the server using module:app format
    uvicorn.run("mcp_panther_module:mcp", host="127.0.0.1", port=8000) 