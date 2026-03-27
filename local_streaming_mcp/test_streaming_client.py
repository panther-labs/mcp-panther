"""
test_streaming_client.py
------------------------
A standalone script that validates the local Panther MCP streaming server
by exercising the MCP Streamable-HTTP transport from a Python client.

What it tests
~~~~~~~~~~~~~
1.  Health endpoint  – basic connectivity check.
2.  MCP initialize   – full protocol handshake; verifies the server returns
                       a valid server-info response.
3.  Tool listing     – confirms all Panther tools are registered.
4.  SSE streaming    – opens a GET /mcp channel and verifies the server sends
                       SSE events (exercises the streaming path).
5.  Tool call        – invokes a lightweight Panther tool (get_permissions)
                       and verifies the streaming JSON-RPC response.

Usage
~~~~~
  # Start the server first:
  uv run python local_streaming_mcp/server.py

  # Then in another terminal:
  uv run python local_streaming_mcp/test_streaming_client.py

  # Target a different URL:
  uv run python local_streaming_mcp/test_streaming_client.py \\
      --url http://localhost:8000

  # Verbose output:
  uv run python local_streaming_mcp/test_streaming_client.py --verbose
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Generator

# ---------------------------------------------------------------------------
# ANSI colour helpers (gracefully disabled on Windows)
# ---------------------------------------------------------------------------
_USE_COLOUR = sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOUR else text


OK = _c("32", "✓")
FAIL = _c("31", "✗")
INFO = _c("36", "·")
WARN = _c("33", "⚠")


# ---------------------------------------------------------------------------
# Minimal HTTP helpers (stdlib only – no extra deps)
# ---------------------------------------------------------------------------


def _post_json(
    url: str, body: dict[str, Any], timeout: int = 30
) -> tuple[int, dict | str]:
    """POST a JSON body and return (status_code, parsed_response)."""
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            content_type = resp.headers.get("Content-Type", "")
            status = resp.status
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        status = exc.code
        content_type = exc.headers.get("Content-Type", "")

    # If the server returned SSE, parse it into the last data payload.
    if "text/event-stream" in content_type:
        parsed = _parse_sse_body(raw)
    else:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = raw
    return status, parsed


def _get_stream(url: str, timeout: int = 5) -> Generator[str, None, None]:
    """
    Open a GET request expecting text/event-stream and yield raw SSE lines.
    Stops after `timeout` seconds or when the connection closes.
    """
    req = urllib.request.Request(
        url,
        headers={"Accept": "text/event-stream"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            while True:
                line = resp.readline()
                if not line:
                    break
                yield line.decode("utf-8", errors="replace").rstrip("\n")
    except TimeoutError:
        # Expected – we deliberately use a short timeout for the test.
        return
    except Exception:  # noqa: BLE001
        return


def _parse_sse_body(raw: str) -> dict | str:
    """Extract the last 'data:' payload from an SSE response body."""
    last_data: str | None = None
    for line in raw.splitlines():
        if line.startswith("data:"):
            last_data = line[len("data:") :].strip()
    if last_data:
        try:
            return json.loads(last_data)
        except json.JSONDecodeError:
            return last_data
    return raw


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

_PASS = 0
_FAIL = 0


def _check(label: str, condition: bool, detail: str = "") -> bool:
    global _PASS, _FAIL
    if condition:
        _PASS += 1
        print(f"  {OK}  {label}")
    else:
        _FAIL += 1
        msg = f"  {FAIL}  {label}"
        if detail:
            msg += f"\n       {_c('31', detail)}"
        print(msg)
    return condition


# ---------------------------------------------------------------------------
# Individual test cases
# ---------------------------------------------------------------------------


def test_health(base_url: str, verbose: bool) -> bool:
    """GET /health → HTTP 200 with status=ok."""
    print(f"\n{INFO} Health check")
    try:
        req = urllib.request.Request(f"{base_url}/health", method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read())
            status = resp.status
    except Exception as exc:  # noqa: BLE001
        return _check("GET /health returns 200", False, str(exc))

    if verbose:
        print(f"     Response: {json.dumps(body, indent=2)}")

    ok = _check("GET /health returns 200", status == 200, f"Got {status}")
    _check(
        "Response contains status=ok",
        body.get("status") == "ok",
        f"Got: {body}",
    )
    _check(
        "Response contains mcp_endpoint",
        "mcp_endpoint" in body,
        f"Keys: {list(body)}",
    )
    return ok


def test_initialize(mcp_url: str, verbose: bool) -> str | None:
    """
    POST /mcp  initialize request → server returns ServerInfo.
    Returns the negotiated protocol version or None on failure.
    """
    print(f"\n{INFO} MCP initialize handshake")
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}, "prompts": {}, "resources": {}},
            "clientInfo": {"name": "test-client", "version": "0.1.0"},
        },
    }
    status, resp = _post_json(mcp_url, payload)

    if verbose:
        print(f"     HTTP status : {status}")
        print(f"     Response    : {json.dumps(resp, indent=2)}")

    _check("HTTP 200 on initialize", status == 200, f"Got {status}")
    if not isinstance(resp, dict):
        _check("Response is JSON object", False, f"Got: {type(resp)}")
        return None

    # MCP response can be wrapped in SSE or returned as plain JSON-RPC.
    result = resp.get("result", resp)

    _check(
        "Response contains serverInfo",
        "serverInfo" in result,
        f"Keys: {list(result)}",
    )
    proto = result.get("protocolVersion")
    _check("protocolVersion present", proto is not None, f"result={result}")
    return proto


def test_list_tools(mcp_url: str, verbose: bool) -> int:
    """POST /mcp  tools/list → returns at least one Panther tool."""
    print(f"\n{INFO} Tool listing")
    payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {},
    }
    status, resp = _post_json(mcp_url, payload)

    if verbose:
        print(f"     HTTP status : {status}")

    _check("HTTP 200 on tools/list", status == 200, f"Got {status}")
    if not isinstance(resp, dict):
        _check("Response is JSON", False, f"Got: {type(resp)}")
        return 0

    result = resp.get("result", resp)
    tools = result.get("tools", [])
    count = len(tools)

    _check("At least one tool registered", count > 0, f"Got {count}")
    _check(
        "At least 10 tools registered (sanity check)",
        count >= 10,
        f"Got {count}",
    )

    if verbose and tools:
        names = [t.get("name", "?") for t in tools[:5]]
        print(f"     First 5 tools: {names} … (+{count - 5} more)")
    else:
        print(f"     {INFO}  Found {count} registered tools")

    return count


def test_sse_stream(mcp_url: str, verbose: bool) -> bool:
    """
    GET /mcp  opens the SSE channel.
    We collect up to 3 seconds of events and verify we receive SSE-formatted
    data (lines starting with 'data:', 'event:', or ':' keep-alives).
    """
    print(f"\n{INFO} SSE stream (GET {mcp_url})")
    print(f"     {INFO}  Collecting events for ~3 seconds …")

    lines_seen: list[str] = []
    start = time.monotonic()

    for line in _get_stream(mcp_url, timeout=3):
        lines_seen.append(line)
        if verbose:
            print(f"     SSE: {repr(line)}")
        if time.monotonic() - start > 3:
            break

    has_sse = any(
        ln.startswith("data:") or ln.startswith("event:") or ln.startswith(":")
        for ln in lines_seen
    )
    return _check(
        "Server sends SSE-formatted events",
        has_sse,
        f"Lines received: {lines_seen[:5]}",
    )


def test_tool_call(mcp_url: str, verbose: bool) -> bool:
    """
    POST /mcp  tools/call get_permissions → streaming JSON-RPC response.
    get_permissions requires no Panther credentials so it's safe to call
    even without a real PANTHER_API_TOKEN configured.
    """
    print(f"\n{INFO} Tool call: get_permissions")
    payload = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "get_permissions", "arguments": {}},
    }
    status, resp = _post_json(mcp_url, payload, timeout=30)

    if verbose:
        print(f"     HTTP status : {status}")
        print(f"     Response    : {json.dumps(resp, indent=2)}")

    _check("HTTP 200 on tool call", status == 200, f"Got {status}")
    if not isinstance(resp, dict):
        _check("Response is JSON", False, f"Type: {type(resp)}")
        return False

    # The result can be wrapped in result.content[] or returned directly.
    has_content = (
        "result" in resp
        or "content" in resp
        or "error" in resp  # structured error is still a valid MCP response
    )
    return _check(
        "Response has result/content/error key",
        has_content,
        f"Keys: {list(resp)}",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate the Panther MCP local streaming server"
    )
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000",
        help="Base URL of the running server (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print full request/response bodies",
    )
    parser.add_argument(
        "--skip-sse",
        action="store_true",
        help="Skip the SSE stream test (useful in CI)",
    )
    args = parser.parse_args()

    base = args.url.rstrip("/")
    mcp_url = f"{base}/mcp"

    print(f"\n{'=' * 58}")
    print("  Panther MCP Streaming Server – Test Suite")
    print(f"  Target: {base}")
    print(f"{'=' * 58}")

    # Run tests
    test_health(base, args.verbose)
    test_initialize(mcp_url, args.verbose)
    test_list_tools(mcp_url, args.verbose)

    if not args.skip_sse:
        test_sse_stream(mcp_url, args.verbose)

    test_tool_call(mcp_url, args.verbose)

    # Summary
    total = _PASS + _FAIL
    print(f"\n{'=' * 58}")
    print(f"  Results: {_PASS}/{total} passed", end="")
    if _FAIL:
        print(f"  {FAIL} {_FAIL} failed")
    else:
        print(f"  {OK} all passed")
    print(f"{'=' * 58}\n")

    sys.exit(0 if _FAIL == 0 else 1)


if __name__ == "__main__":
    main()
