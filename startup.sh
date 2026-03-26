#!/bin/bash
# Startup script for Azure Functions self-hosted MCP server.
# Starts the server with streamable-http transport so Azure Functions
# can proxy requests to it.
set -e

# Resolve Python from the virtual environment if present.
# Local dev: uv sync pre-installs everything into .venv, so no install step
#            is needed — just run the server using the venv Python directly.
# Azure:     no .venv exists, so fall back to system Python and install first.
if [ -f ".venv/Scripts/python.exe" ]; then
    # Windows (Git Bash) - venv created by uv sync
    PYTHON=".venv/Scripts/python.exe"
elif [ -f ".venv/bin/python" ]; then
    # macOS / Linux / WSL - venv created by uv sync
    PYTHON=".venv/bin/python"
else
    # Azure Functions - no local venv, install from source using system Python
    PYTHON="python"
    echo "Installing mcp-panther..."
    "$PYTHON" -m pip install -q .
fi

echo "Starting Panther MCP server on port 8080..."
exec "$PYTHON" -m mcp_panther.server \
    --transport streamable-http \
    --host 0.0.0.0 \
    --port 8080
