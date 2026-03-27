"""
panther_mcp_app.py
------------------
Factory module for creating the FastMCP server instance used by both the
Azure Functions handler and any alternative ASGI host.

Responsibilities:
  - Add the parent repo's src/ directory to sys.path so that
    `mcp_panther` can be imported regardless of how this module is loaded
    (local dev, Azure Functions worker, container, etc.).
  - Instantiate a FastMCP server with the Panther aiohttp lifespan that
    manages connection pools.
  - Register every tool, prompt, and resource from panther_mcp_core.
  - Expose `get_asgi_app()` which returns a Starlette ASGI application
    implementing the MCP Streamable-HTTP transport.

The module-level singleton (`_mcp_instance`) means the server is created
once per process.  Azure Functions warm-starts reuse the same process, so
the lifespan (and the aiohttp connector pools it holds) survive across
multiple invocations on the same worker instance.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP
    from starlette.applications import Starlette

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path bootstrapping
# ---------------------------------------------------------------------------
# When deployed to Azure Functions the mcp_panther package must either be
# installed (listed in requirements.txt) or discoverable via sys.path.
# During local development the package lives in <repo_root>/src/; we add that
# directory here so both scenarios work without any extra configuration.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_THIS_DIR)
_SRC_DIR = os.path.join(_REPO_ROOT, "src")

if os.path.isdir(_SRC_DIR) and _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)
    logger.debug("Added %s to sys.path for mcp_panther imports", _SRC_DIR)

# ---------------------------------------------------------------------------
# Deferred import of panther_mcp_core
# ---------------------------------------------------------------------------
# We import after the path manipulation above so that both installed-package
# and source-tree deployments work.
try:
    from mcp_panther.panther_mcp_core.client import lifespan
    from mcp_panther.panther_mcp_core.prompts.registry import register_all_prompts
    from mcp_panther.panther_mcp_core.resources.registry import register_all_resources
    from mcp_panther.panther_mcp_core.tools.registry import register_all_tools
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "Could not import mcp_panther.  Either install the package "
        "(pip install -e <repo_root>) or ensure <repo_root>/src is on "
        "PYTHONPATH.\n"
        f"Original error: {exc}"
    ) from exc

# ---------------------------------------------------------------------------
# Server name
# ---------------------------------------------------------------------------
MCP_SERVER_NAME = "panther-mcp-azure"

# Module-level singleton – created once per worker process.
_mcp_instance: FastMCP | None = None


def create_mcp_server() -> "FastMCP":
    """
    Create (or return the cached) FastMCP server with all Panther capabilities.

    Thread/task safety: FastMCP and the underlying aiohttp pools are designed
    for async use.  In Azure Functions each worker process handles one request
    at a time by default, so the singleton pattern is safe.  If you switch to
    a multi-threaded worker model, add a threading.Lock around this function.

    Returns:
        Configured FastMCP instance.
    """
    global _mcp_instance

    if _mcp_instance is not None:
        # Warm-start: reuse the existing server without re-registering tools.
        return _mcp_instance

    logger.info("Initialising FastMCP server '%s'", MCP_SERVER_NAME)

    from fastmcp import FastMCP  # local import to keep module load fast

    mcp = FastMCP(
        name=MCP_SERVER_NAME,
        lifespan=lifespan,  # manages aiohttp connection pools
        instructions=(
            "Panther MCP server running on Azure Functions.  "
            "Provides tools for alert triage, detection management, "
            "data-lake querying, and security operations."
        ),
    )

    # Register all Panther capabilities.  Each register_* call iterates the
    # module-level registry populated by @mcp_tool / @mcp_prompt / @mcp_resource
    # decorators when the tool/prompt/resource modules were first imported.
    register_all_tools(mcp)
    register_all_prompts(mcp)
    register_all_resources(mcp)

    logger.info("FastMCP server '%s' initialised successfully", MCP_SERVER_NAME)
    _mcp_instance = mcp
    return mcp


def get_asgi_app(*, stateless_http: bool = False) -> "Starlette":
    """
    Return the ASGI application that implements the MCP Streamable-HTTP transport.

    The returned object is a ``fastmcp.server.http.StarletteWithLifespan``
    instance (a Starlette subclass).  It can be:
      - Wrapped with ``azure.functions.AsgiMiddleware`` for Azure Functions.
      - Passed directly to ``uvicorn.run()`` for local development.
      - Mounted as a sub-application inside any ASGI framework.

    Args:
        stateless_http:
            When True, the server operates in stateless mode – each request is
            processed independently with no shared SSE session state.  This is
            the safest choice for Azure Functions Consumption plan where
            persistent connections are not guaranteed.  Set to False (default)
            if you need server-initiated SSE pushes (requires Premium/Dedicated
            plan or a container-based deployment).

    Returns:
        Starlette ASGI application.
    """
    mcp = create_mcp_server()

    # http_app() creates a Starlette app that speaks the MCP Streamable-HTTP
    # transport.  The transport='streamable-http' value selects the modern
    # MCP HTTP+SSE protocol (vs. the legacy 'sse' transport).
    # The path=None default mounts the MCP handler at "/mcp".
    return mcp.http_app(
        transport="streamable-http",
        stateless_http=stateless_http,
    )
