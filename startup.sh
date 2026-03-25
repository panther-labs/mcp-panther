#!/bin/bash
# Startup script for Azure Functions self-hosted MCP server.
# Installs the mcp-panther package from source then starts the server
# with streamable-http transport so Azure Functions can proxy requests to it.
set -e

# Activate the virtual environment if present so that pip and python resolve
# correctly. This handles local development on all platforms:
#   macOS / Linux / WSL  → .venv/bin/activate
#   Windows (Git Bash)   → .venv/Scripts/activate
# On Azure the venv does not exist and system pip/python are used instead.
if [ -f ".venv/bin/activate" ]; then
    source ".venv/bin/activate"
elif [ -f ".venv/Scripts/activate" ]; then
    source ".venv/Scripts/activate"
fi

echo "Installing mcp-panther..."
pip install -q .

echo "Starting Panther MCP server on port 8080..."
exec python -m mcp_panther.server \
    --transport streamable-http \
    --host 0.0.0.0 \
    --port 8080
