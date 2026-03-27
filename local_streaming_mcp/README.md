# Panther MCP Server – Local Streaming (HTTP)

A standalone **local development server** that exposes the full Panther MCP
toolset over **HTTP streaming** (MCP Streamable-HTTP transport) – no stdio,
no Docker required.

Use this when you want to:
- Develop and test without a full Docker or cloud setup.
- Point multiple MCP clients at a single running instance.
- Debug streaming behaviour with real SSE events visible in the terminal.
- Mirror the Azure Functions deployment locally before pushing.

---

## Architecture

```
MCP Client (Claude Code / Cursor / etc.)
        │
        │  POST /mcp   JSON-RPC request
        │  GET  /mcp   Open SSE channel (server-initiated messages)
        ▼
┌─────────────────────────────────────────────────────┐
│              Uvicorn (ASGI server)                   │
│                                                     │
│  /health  ──►  JSON health-check endpoint           │
│  /mcp     ──►  FastMCP StreamableHTTP handler       │
│                 ├─ POST: execute tool / prompt       │
│                 └─ GET:  SSE event stream            │
│                                                     │
│  FastMCP server                                     │
│   ├─ All Panther tools   (list_alerts, etc.)        │
│   ├─ All Panther prompts (alert_triage, etc.)       │
│   └─ All Panther resources (config://panther)       │
└─────────────────────────────────────────────────────┘
        │
        │  GraphQL / REST (aiohttp persistent connection pool)
        ▼
  Panther SIEM API
```

---

## Prerequisites

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/) (recommended) **or** pip
- `PANTHER_INSTANCE_URL` and `PANTHER_API_TOKEN` environment variables

---

## Quick Start

### 1. Install dependencies (from the repo root)

```bash
# Using uv (recommended):
uv sync

# Or pip:
pip install -e .
pip install uvicorn starlette
```

### 2. Set environment variables

```bash
export PANTHER_INSTANCE_URL="https://your-tenant.runpanther.io"
export PANTHER_API_TOKEN="your-api-token"
```

### 3. Start the server

```bash
# From the repo root:
uv run python local_streaming_mcp/server.py
```

You should see:

```
╔══════════════════════════════════════════════════════════╗
║          Panther MCP  –  Local Streaming Server          ║
╠══════════════════════════════════════════════════════════╣
║  Transport  :  MCP Streamable-HTTP                       ║
║  MCP URL    :  http://127.0.0.1:8000/mcp                 ║
║  Health     :  http://127.0.0.1:8000/health              ║
╠══════════════════════════════════════════════════════════╣
║  Configure Claude Code:                                  ║
║  claude mcp add-json panther-local \                     ║
║    '{"url": "http://127.0.0.1:8000/mcp"}'               ║
╚══════════════════════════════════════════════════════════╝
```

### 4. Connect your MCP client

**Claude Code:**
```bash
claude mcp add-json panther-local '{"url": "http://127.0.0.1:8000/mcp"}'
```

**Claude Desktop / Cursor** (add to config JSON):
```json
{
  "mcpServers": {
    "panther-local": {
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```

---

## Configuration

All options can be set via environment variables or CLI flags.

| Env var | CLI flag | Default | Description |
|---------|----------|---------|-------------|
| `MCP_HOST` | `--host` | `127.0.0.1` | Bind address |
| `MCP_PORT` | `--port` | `8000` | Port to listen on |
| `LOG_LEVEL` | – | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `STATELESS_HTTP` | – | `false` | `"true"` for stateless SSE mode |
| `PANTHER_INSTANCE_URL` | – | **required** | Panther base URL |
| `PANTHER_API_TOKEN` | – | **required** | Panther API token |

### Custom port example

```bash
uv run python local_streaming_mcp/server.py --port 9000
```

### Bind to all interfaces (for network access)

```bash
uv run python local_streaming_mcp/server.py --host 0.0.0.0
```

### Auto-reload on source changes (development)

```bash
uv run python local_streaming_mcp/server.py --reload
```

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check – returns `{"status": "ok", ...}` |
| `POST` | `/mcp` | MCP JSON-RPC request (tool calls, prompts, resources) |
| `GET` | `/mcp` | Open SSE channel for server-initiated messages |
| `DELETE` | `/mcp` | Close SSE session |

---

## Example Requests

### Health check

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "ok",
  "server": "panther-mcp-local",
  "transport": "streamable-http",
  "mcp_endpoint": "/mcp"
}
```

### MCP initialize handshake

```bash
curl -s -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {"name": "curl-test", "version": "1.0"}
    }
  }'
```

### List available tools

```bash
curl -s -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | python3 -c "import sys,json; r=json.load(sys.stdin); \
    print('\n'.join(t['name'] for t in r.get('result',{}).get('tools',[])))"
```

### Call a tool

```bash
curl -s -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "list_alerts",
      "arguments": {
        "severities": ["CRITICAL", "HIGH"],
        "page_size": 5
      }
    }
  }'
```

### Open an SSE channel and watch events stream in

```bash
curl -N -H "Accept: text/event-stream" http://localhost:8000/mcp
```

You will see raw SSE events like:

```
event: endpoint
data: /mcp?sessionId=abc123...

: keep-alive

data: {"jsonrpc":"2.0","method":"notifications/...","params":{...}}
```

---

## Validate Streaming with the Test Client

A test script is included to exercise all key paths of the streaming server:

```bash
# Make sure the server is running first, then:
uv run python local_streaming_mcp/test_streaming_client.py

# Verbose output (prints full request/response bodies):
uv run python local_streaming_mcp/test_streaming_client.py --verbose

# Target a different URL:
uv run python local_streaming_mcp/test_streaming_client.py --url http://localhost:9000

# Skip the SSE stream test (useful in CI without a TTY):
uv run python local_streaming_mcp/test_streaming_client.py --skip-sse
```

Expected output:

```
==========================================================
  Panther MCP Streaming Server – Test Suite
  Target: http://127.0.0.1:8000
==========================================================

· Health check
  ✓  GET /health returns 200
  ✓  Response contains status=ok
  ✓  Response contains mcp_endpoint

· MCP initialize handshake
  ✓  HTTP 200 on initialize
  ✓  Response contains serverInfo
  ✓  protocolVersion present

· Tool listing
  ✓  At least one tool registered
  ✓  At least 10 tools registered (sanity check)
  ·  Found 42 registered tools

· SSE stream (GET http://127.0.0.1:8000/mcp)
  ·  Collecting events for ~3 seconds …
  ✓  Server sends SSE-formatted events

· Tool call: get_permissions
  ✓  HTTP 200 on tool call
  ✓  Response has result/content/error key

==========================================================
  Results: 11/11 passed  ✓ all passed
==========================================================
```

---

## How Streaming Works

### MCP Streamable-HTTP transport

The server implements the [MCP Streamable-HTTP transport](https://spec.modelcontextprotocol.io/specification/2024-11-05/basic/transports/#streamable-http).

```
Client                              Server
  │                                    │
  │──── POST /mcp (JSON-RPC req) ─────►│
  │                                    │  (processes request)
  │◄─── Content-Type: text/event-stream│
  │                                    │
  │  data: {"jsonrpc":"2.0","id":1,... │  (first chunk arrives immediately)
  │  data: {"jsonrpc":"2.0","method":..│  (progress notifications stream in)
  │  data: {"jsonrpc":"2.0","id":1,... │  (final result)
  │                                    │
  │──── GET /mcp ──────────────────────►│  (open SSE channel)
  │◄─── event: endpoint ───────────────│
  │     data: /mcp?sessionId=xxx        │
  │                                    │
  │◄─── : keep-alive ──────────────────│  (periodic keep-alives)
```

### Key properties

- **Incremental delivery**: Long-running tool calls (e.g. `query_data_lake`) can
  emit progress notifications before the final result arrives.
- **No buffering**: uvicorn streams responses directly to the client; responses
  are not accumulated in memory.
- **Concurrent requests**: uvicorn handles multiple connections concurrently via
  asyncio; the aiohttp connection pool (managed by the FastMCP lifespan) is
  shared across all requests.

---

## Differences from the Existing STDIO Server

| Feature | STDIO server (`mcp-panther`) | Local streaming server |
|---------|------------------------------|------------------------|
| Transport | stdio (stdin/stdout) | HTTP (Streamable-HTTP) |
| Multiple clients | No (1:1 with parent process) | Yes (concurrent HTTP connections) |
| Network accessible | No | Yes (configurable bind address) |
| Health check | No | `GET /health` |
| Streaming protocol | MCP framing over pipes | SSE over HTTP |
| Start command | `mcp-panther` or `uv run mcp-panther` | `uv run python local_streaming_mcp/server.py` |

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'mcp_panther'`

Run `uv sync` from the repo root, or `pip install -e .`.

### `ModuleNotFoundError: No module named 'uvicorn'`

```bash
pip install uvicorn
# or: uv pip install uvicorn
```

### `Address already in use`

Another process is using port 8000.  Either stop it or change the port:
```bash
uv run python local_streaming_mcp/server.py --port 8080
```

### Tool returns `{"success": false, "message": "Request failed (HTTP 403)"}`

Your `PANTHER_API_TOKEN` lacks the permissions required by that tool.  Refer
to the tool's description for the required permissions, and update the token
in Panther's **Settings → API Tokens**.

### SSE events not appearing

Ensure you pass `-N` (no-buffer) and the correct `Accept` header to curl:
```bash
curl -N -H "Accept: text/event-stream" http://localhost:8000/mcp
```
Some proxies buffer SSE; test with a direct connection first.
