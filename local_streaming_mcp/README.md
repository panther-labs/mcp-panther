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

### macOS

**Python 3.12+**
```bash
# Option A – Homebrew (recommended)
brew install python@3.12

# Option B – python.org installer
# Download from https://www.python.org/downloads/macos/
```

**uv** (recommended package manager)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# or via Homebrew:
brew install uv
```

### Linux

**Python 3.12+**
```bash
# Debian / Ubuntu
sudo apt update && sudo apt install python3.12 python3.12-venv python3-pip

# Fedora / RHEL / CentOS
sudo dnf install python3.12

# Arch
sudo pacman -S python

# Or use pyenv for any distro:
curl https://pyenv.run | bash
pyenv install 3.12
pyenv global 3.12
```

**uv** (recommended package manager)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Windows

**Python 3.12+**

Install from the [Microsoft Store](https://apps.microsoft.com/detail/9ncvdn91xzqp)
or the [python.org installer](https://www.python.org/downloads/windows/).
During installation, check **"Add Python to PATH"**.

**uv** (recommended package manager) – run in PowerShell:
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

> PowerShell 7+ is recommended over the legacy Command Prompt for the best
> experience. Install it from the
> [Microsoft Store](https://apps.microsoft.com/detail/9n0dx20hk701).

---

## Quick Start

### Step 1 – Clone the repo and install dependencies

**macOS / Linux**
```bash
git clone https://github.com/panther-labs/mcp-panther.git
cd mcp-panther
uv sync
```

**Windows – PowerShell**
```powershell
git clone https://github.com/panther-labs/mcp-panther.git
cd mcp-panther
uv sync
```

> If you prefer plain pip over uv, run `pip install -e .` followed by
> `pip install uvicorn starlette` on any platform.

---

### Step 2 – Set environment variables

**macOS / Linux** (bash or zsh)
```bash
export PANTHER_INSTANCE_URL="https://your-tenant.runpanther.io"
export PANTHER_API_TOKEN="your-api-token"
```

To persist across sessions, add the two lines above to `~/.zshrc` (macOS default)
or `~/.bashrc` (Linux default), then `source` the file.

**Windows – PowerShell**
```powershell
$env:PANTHER_INSTANCE_URL = "https://your-tenant.runpanther.io"
$env:PANTHER_API_TOKEN    = "your-api-token"
```

To persist permanently in PowerShell:
```powershell
[System.Environment]::SetEnvironmentVariable("PANTHER_INSTANCE_URL","https://your-tenant.runpanther.io","User")
[System.Environment]::SetEnvironmentVariable("PANTHER_API_TOKEN","your-api-token","User")
```

**Windows – Command Prompt**
```cmd
set PANTHER_INSTANCE_URL=https://your-tenant.runpanther.io
set PANTHER_API_TOKEN=your-api-token
```

---

### Step 3 – Start the server

The start command is the same on all platforms:

```bash
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

---

### Step 4 – Connect your MCP client

**Claude Code** (all platforms):
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

### Custom port

```bash
uv run python local_streaming_mcp/server.py --port 9000
```

### Bind to all interfaces (for LAN access)

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

Works identically on macOS, Linux, and Windows:

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

---

### MCP initialize handshake

**macOS / Linux**
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

**Windows – PowerShell**
```powershell
Invoke-RestMethod -Method Post http://localhost:8000/mcp `
  -ContentType "application/json" `
  -Headers @{ Accept = "application/json, text/event-stream" } `
  -Body '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"curl-test","version":"1.0"}}}'
```

**Windows – Command Prompt** (curl.exe, available on Windows 10/11)
```cmd
curl -s -X POST http://localhost:8000/mcp ^
  -H "Content-Type: application/json" ^
  -H "Accept: application/json, text/event-stream" ^
  -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2024-11-05\",\"capabilities\":{},\"clientInfo\":{\"name\":\"curl-test\",\"version\":\"1.0\"}}}"
```

---

### List available tools

**macOS / Linux**
```bash
curl -s -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | python3 -c "import sys,json; r=json.load(sys.stdin); \
    print('\n'.join(t['name'] for t in r.get('result',{}).get('tools',[])))"
```

**Windows – PowerShell**
```powershell
$r = Invoke-RestMethod -Method Post http://localhost:8000/mcp `
  -ContentType "application/json" `
  -Headers @{ Accept = "application/json, text/event-stream" } `
  -Body '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
$r.result.tools | Select-Object -ExpandProperty name
```

---

### Call a tool

**macOS / Linux**
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

**Windows – PowerShell**
```powershell
Invoke-RestMethod -Method Post http://localhost:8000/mcp `
  -ContentType "application/json" `
  -Headers @{ Accept = "application/json, text/event-stream" } `
  -Body '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"list_alerts","arguments":{"severities":["CRITICAL","HIGH"],"page_size":5}}}'
```

---

### Open an SSE channel and watch events stream in

**macOS / Linux**
```bash
curl -N -H "Accept: text/event-stream" http://localhost:8000/mcp
```

**Windows – PowerShell** (streams until Ctrl+C)
```powershell
$req = [System.Net.WebRequest]::Create("http://localhost:8000/mcp")
$req.Headers.Add("Accept", "text/event-stream")
$stream = $req.GetResponse().GetResponseStream()
$reader = [System.IO.StreamReader]::new($stream)
while (-not $reader.EndOfStream) { Write-Host $reader.ReadLine() }
```

**Windows – Command Prompt**
```cmd
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

A test script is included to exercise all key paths of the streaming server.
It uses only the Python standard library – no extra dependencies needed.

```bash
# Make sure the server is running first, then (all platforms):
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
# or:
uv pip install uvicorn
```

### `Address already in use`

Another process is using port 8000. Find and stop it, or use a different port.

**macOS**
```bash
lsof -i :8000
kill -9 <PID>
```

**Linux**
```bash
# Option A – lsof (install with: sudo apt install lsof)
lsof -i :8000
kill -9 <PID>

# Option B – ss (available on most modern distros without extra install)
ss -tulpn | grep :8000
kill -9 <PID>
```

**Windows – PowerShell**
```powershell
netstat -ano | findstr :8000
# Note the PID in the last column, then:
Stop-Process -Id <PID>
```

**Windows – Command Prompt**
```cmd
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

Or just change the port on any platform:
```bash
uv run python local_streaming_mcp/server.py --port 8080
```

### Tool returns `{"success": false, "message": "Request failed (HTTP 403)"}`

Your `PANTHER_API_TOKEN` lacks the permissions required by that tool. Refer
to the tool's description for the required permissions, and update the token
in Panther's **Settings → API Tokens**.

### SSE events not appearing

**macOS / Linux** – pass `-N` (no-buffer) and the correct `Accept` header:
```bash
curl -N -H "Accept: text/event-stream" http://localhost:8000/mcp
```

**Windows** – `curl.exe` in Windows 10/11 supports `-N` but may buffer through
the terminal. Use the PowerShell `StreamReader` example above for reliable
line-by-line output.

Some corporate proxies buffer SSE regardless of platform; test with a direct
connection (bypass the proxy) first.

### `uv` command not found after install

**macOS / Linux** – restart your terminal or source your shell profile:
```bash
source ~/.zshrc   # macOS default shell
source ~/.bashrc  # Linux default shell
```

**Windows** – close and reopen PowerShell, or run:
```powershell
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","User")
```
