#!/bin/bash
# Startup script for Azure Functions self-hosted MCP server.
# Installs the mcp-panther package from source then starts the server
# with streamable-http transport so Azure Functions can proxy requests to it.
set -e

echo "Installing mcp-panther..."
pip install -q .

echo "Starting Panther MCP server on port 8080..."
exec python -m mcp_panther.server \
    --transport streamable-http \
    --host 0.0.0.0 \
    --port 8080
