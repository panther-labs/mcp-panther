#!/bin/bash
# Startup script for Azure Functions self-hosted MCP server.
# Starts the server with streamable-http transport so Azure Functions
# can proxy requests to it.
set -e

# Prefer uv if available. uv run handles venv activation and dependency
# resolution without requiring pip, which uv-created venvs omit by default.
if command -v uv &>/dev/null; then
    echo "Starting Panther MCP server via uv..."
    exec uv run python -m mcp_panther.server \
        --transport streamable-http \
        --host 0.0.0.0 \
        --port 8080
fi

# Fallback for Azure Functions where uv is not installed.
# Resolve Python from the venv if present, otherwise use system Python.
if [ -f ".venv/Scripts/python.exe" ]; then
    PYTHON=".venv/Scripts/python.exe"
elif [ -f ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="python"
fi

echo "Installing mcp-panther..."
"$PYTHON" -m pip install -q .

echo "Starting Panther MCP server on port 8080..."
exec "$PYTHON" -m mcp_panther.server \
    --transport streamable-http \
    --host 0.0.0.0 \
    --port 8080
