"""
function_app.py
---------------
Azure Functions v2 (Python programming model) entry point for the
Panther MCP streaming server.

Architecture
~~~~~~~~~~~~
                        ┌─────────────────────────────────┐
 MCP Client             │        Azure Function App        │
 (Claude / LLM)  HTTP   │                                  │
 ─────────────── ─────► │  mcp_handler()                   │
                        │   └─ AsgiMiddleware               │
                        │       └─ FastMCP Starlette app    │
                        │           └─ Panther tools/prompts│
                        └─────────────────────────────────┘

Transport
~~~~~~~~~
The MCP Streamable-HTTP transport uses:
  POST /mcp   – client sends a JSON-RPC request; server responds with
                either application/json (single response) or
                text/event-stream (streamed SSE response).
  GET  /mcp   – client opens a persistent SSE channel for server-initiated
                messages (only supported on non-Consumption plans).
  DELETE /mcp – client tears down the SSE session.

Azure Functions limitations
~~~~~~~~~~~~~~~~~~~~~~~~~~~
  • Consumption plan: 10-minute default timeout limits long-lived SSE.
    Use `stateless_http=True` (set STATELESS_HTTP=true env var) to avoid
    session state; each POST is handled independently.
  • Premium / Dedicated plan: supports long-lived SSE connections with
    WEBSITE_SOCKET_TIMEOUT set appropriately.
  • For true streaming responses, ensure the Function App uses the
    Python v2 programming model and azure-functions >= 1.18.0.

Environment variables required
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  PANTHER_INSTANCE_URL  – e.g. https://your-tenant.runpanther.io
  PANTHER_API_TOKEN     – API token with required permissions
  STATELESS_HTTP        – "true" to enable stateless mode (default: false)
  LOG_LEVEL             – Python log level (default: WARNING)
"""

from __future__ import annotations

import logging
import os

import azure.functions as func
from panther_mcp_app import get_asgi_app

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
log_level_name = os.environ.get("LOG_LEVEL", "WARNING").upper()
logging.basicConfig(
    level=getattr(logging, log_level_name, logging.WARNING),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("panther-mcp-azure")

# ---------------------------------------------------------------------------
# Build the ASGI app once at module load time.
# Azure Functions re-uses the worker process for warm starts, so the FastMCP
# server (and its aiohttp connection pools) survive across invocations.
# ---------------------------------------------------------------------------
_stateless = os.environ.get("STATELESS_HTTP", "false").lower() == "true"

logger.info("Loading Panther MCP ASGI app (stateless_http=%s)", _stateless)

_asgi_app = get_asgi_app(stateless_http=_stateless)

# Wrap the Starlette app with Azure's ASGI adapter once; reuse for every call.
_asgi_middleware = func.AsgiMiddleware(_asgi_app)

# ---------------------------------------------------------------------------
# Azure Functions app definition
# ---------------------------------------------------------------------------
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.route(
    route="{*route}",  # Catch-all: forwards /mcp, /mcp/, etc.
    methods=["GET", "POST", "DELETE"],
)
async def mcp_handler(
    req: func.HttpRequest,
    context: func.Context,
) -> func.HttpResponse:
    """
    HTTP-triggered Azure Function that proxies all MCP protocol requests
    to the FastMCP Starlette application via ASGI.

    The MCP client (e.g. Claude Code) will target:
      POST https://<func-app>.azurewebsites.net/api/mcp
      GET  https://<func-app>.azurewebsites.net/api/mcp   (SSE channel)

    Note: Azure Functions automatically prefixes routes with /api/ unless
    you configure `routePrefix` to "" in host.json.
    """
    logger.debug(
        "MCP request: method=%s path=%s",
        req.method,
        req.url,
    )

    # Delegate entirely to the FastMCP ASGI app.
    # AsgiMiddleware translates the func.HttpRequest into an ASGI scope/receive
    # and converts the ASGI send calls back into a func.HttpResponse.
    return await _asgi_middleware.handle_async(req, context)
