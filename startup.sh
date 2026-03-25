#!/bin/bash
# Startup script for Azure Functions self-hosted MCP server.
# Installs the mcp-panther package from source then starts the server
# with streamable-http transport so Azure Functions can proxy requests to it.
set -e

# Resolve the Python executable from the virtual environment using a direct
# path lookup. Sourcing the activate script is unreliable inside the bash
# subprocess spawned by Azure Functions Core Tools on Windows because the
# PATH update does not propagate correctly. Using python -m pip also avoids
# needing a standalone pip executable on PATH.
if [ -f ".venv/Scripts/python.exe" ]; then
    # Windows (Git Bash / uv venv)
    PYTHON=".venv/Scripts/python.exe"
elif [ -f ".venv/bin/python" ]; then
    # macOS / Linux / WSL
    PYTHON=".venv/bin/python"
else
    # Azure or any environment where no local venv is present
    PYTHON="python"
fi

echo "Installing mcp-panther..."
"$PYTHON" -m pip install -q .

echo "Starting Panther MCP server on port 8080..."
exec "$PYTHON" -m mcp_panther.server \
    --transport streamable-http \
    --host 0.0.0.0 \
    --port 8080
