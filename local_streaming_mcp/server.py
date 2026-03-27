"""
server.py
---------
Standalone local streaming MCP server for development and testing.

This server exposes the full Panther MCP toolset over the MCP
Streamable-HTTP transport on a plain HTTP socket – no stdio, no Docker
required.

Architecture
~~~~~~~~~~~~

  MCP Client (e.g. Claude Code)
       │
       │  POST /mcp   JSON-RPC request
       │  GET  /mcp   Open SSE stream for server messages
       ▼
  ┌─────────────────────────────────────────────────────┐
  │  Uvicorn (ASGI server)                              │
  │  ├─ /mcp  ──► FastMCP Streamable-HTTP handler       │
  │  │              └─ Panther tools / prompts /         │
  │  │                 resources (from mcp_panther pkg) │
  │  └─ /health ──► lightweight health-check endpoint   │
  └─────────────────────────────────────────────────────┘

Usage
~~~~~
  # From the repo root (installs package in editable mode first):
  uv run python local_streaming_mcp/server.py

  # Or with explicit env vars:
  PANTHER_INSTANCE_URL=https://tenant.runpanther.io \\
  PANTHER_API_TOKEN=your-token \\
  uv run python local_streaming_mcp/server.py --port 8000

  # Configure Claude Code to use it:
  claude mcp add-json panther-local '{
    "url": "http://localhost:8000/mcp"
  }'

Environment variables
~~~~~~~~~~~~~~~~~~~~~
  PANTHER_INSTANCE_URL  – Panther instance base URL (required)
  PANTHER_API_TOKEN     – API token (required)
  MCP_HOST              – Bind address (default: 127.0.0.1)
  MCP_PORT              – Port (default: 8000)
  LOG_LEVEL             – Python log level (default: INFO)
  STATELESS_HTTP        – "true" for stateless SSE mode (default: false)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

# ---------------------------------------------------------------------------
# Path bootstrapping – allow running without installing the package
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_THIS_DIR)
_SRC_DIR = os.path.join(_REPO_ROOT, "src")

if os.path.isdir(_SRC_DIR) and _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

# ---------------------------------------------------------------------------
# Logging (configure before importing FastMCP to capture its startup logs)
# ---------------------------------------------------------------------------
_log_level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
_log_level = getattr(logging, _log_level_name, logging.INFO)

logging.basicConfig(
    level=_log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("panther-mcp-local")

# Ensure FastMCP logs flow through the same handler.
_fastmcp_logger = logging.getLogger("FastMCP")
_fastmcp_logger.propagate = True
_fastmcp_logger.setLevel(_log_level)

# ---------------------------------------------------------------------------
# Import Panther core
# ---------------------------------------------------------------------------
try:
    from mcp_panther.panther_mcp_core.client import lifespan
    from mcp_panther.panther_mcp_core.prompts.registry import register_all_prompts
    from mcp_panther.panther_mcp_core.resources.registry import register_all_resources
    from mcp_panther.panther_mcp_core.tools.registry import register_all_tools
except ImportError as exc:
    logger.error(
        "Could not import mcp_panther.  Run `uv sync` from the repo root "
        "or install the package with `pip install -e <repo_root>`.\n"
        "Error: %s",
        exc,
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Build the FastMCP server
# ---------------------------------------------------------------------------
from fastmcp import FastMCP  # noqa: E402 – after path setup

MCP_SERVER_NAME = "panther-mcp-local"

logger.info("Initialising FastMCP server '%s'", MCP_SERVER_NAME)

mcp = FastMCP(
    name=MCP_SERVER_NAME,
    lifespan=lifespan,
    instructions=(
        "Panther MCP server running locally over HTTP streaming.  "
        "Provides tools for alert triage, detection management, "
        "data-lake querying, and security operations."
    ),
)

register_all_tools(mcp)
register_all_prompts(mcp)
register_all_resources(mcp)

logger.info("Registered all Panther tools, prompts, and resources")

# ---------------------------------------------------------------------------
# Compose the final ASGI application
#
# We wrap FastMCP's Starlette app inside a thin Starlette router so we can
# add a /health endpoint without touching FastMCP internals.
# ---------------------------------------------------------------------------

from starlette.applications import Starlette  # noqa: E402
from starlette.requests import Request  # noqa: E402, TC002
from starlette.responses import JSONResponse  # noqa: E402
from starlette.routing import Mount, Route  # noqa: E402


async def health_check(request: Request) -> JSONResponse:
    """
    Lightweight health-check endpoint.

    Returns HTTP 200 with a JSON body so load-balancers, Azure health probes,
    and ``curl`` users can verify the server is up before sending MCP traffic.
    """
    return JSONResponse(
        {
            "status": "ok",
            "server": MCP_SERVER_NAME,
            "transport": "streamable-http",
            "mcp_endpoint": "/mcp",
        }
    )


_stateless = os.environ.get("STATELESS_HTTP", "false").lower() == "true"

# mcp.http_app() returns a StarletteWithLifespan ASGI app.
# transport='streamable-http' selects the modern MCP HTTP+SSE protocol.
_mcp_asgi = mcp.http_app(
    transport="streamable-http",
    stateless_http=_stateless,
)

# Mount the MCP app at /mcp and add a /health route alongside it.
# The lifespan from _mcp_asgi is automatically propagated by Starlette when
# the app is mounted, so aiohttp connection pools are managed correctly.
asgi_app = Starlette(
    routes=[
        Route("/health", health_check, methods=["GET"]),
        # Mount everything else to the FastMCP Starlette sub-application.
        # This preserves the SSE streaming and all MCP protocol handling.
        Mount("/", app=_mcp_asgi),
    ],
    lifespan=_mcp_asgi.lifespan if hasattr(_mcp_asgi, "lifespan") else None,
)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    """Parse CLI args and start the uvicorn server."""
    parser = argparse.ArgumentParser(
        description="Panther MCP local streaming server (Streamable-HTTP transport)"
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("MCP_HOST", "127.0.0.1"),
        help="Bind address (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("MCP_PORT", "8000")),
        help="Port to listen on (default: 8000)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=False,
        help="Enable auto-reload on source changes (dev only)",
    )
    args = parser.parse_args()

    try:
        import uvicorn
    except ImportError:
        logger.error("uvicorn is not installed.  Install it with: pip install uvicorn")
        sys.exit(1)

    _print_banner(args.host, args.port)

    uvicorn.run(
        # Pass the module:attribute string when --reload is active so uvicorn
        # can re-import the module.  Otherwise pass the app object directly.
        "local_streaming_mcp.server:asgi_app" if args.reload else asgi_app,
        host=args.host,
        port=args.port,
        log_level=_log_level_name.lower(),
        reload=args.reload,
    )


def _print_banner(host: str, port: int) -> None:
    """Print a friendly startup banner."""
    url = f"http://{host}:{port}"
    print(  # noqa: T201
        f"""
╔══════════════════════════════════════════════════════════╗
║          Panther MCP  –  Local Streaming Server          ║
╠══════════════════════════════════════════════════════════╣
║  Transport  :  MCP Streamable-HTTP                       ║
║  MCP URL    :  {url}/mcp{" " * (40 - len(url))}║
║  Health     :  {url}/health{" " * (37 - len(url))}║
╠══════════════════════════════════════════════════════════╣
║  Configure Claude Code:                                  ║
║  claude mcp add-json panther-local \\                     ║
║    '{{"url": "{url}/mcp"}}'             ║
╚══════════════════════════════════════════════════════════╝
"""
    )


if __name__ == "__main__":
    main()
