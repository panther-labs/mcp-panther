# Panther MCP Server – Azure Functions Deployment

This directory contains everything needed to deploy the Panther MCP server
as an **Azure Functions** application with **Streamable-HTTP** transport.

---

## Architecture

```
MCP Client (Claude Code / Cursor / etc.)
        │
        │  HTTP  POST /mcp  (JSON-RPC request)
        │  HTTP  GET  /mcp  (SSE channel – server-initiated messages)
        ▼
┌─────────────────────────────────────────────────────┐
│              Azure Function App                      │
│                                                     │
│  mcp_handler()  [HTTP trigger, catch-all route]     │
│   └─ azure.functions.AsgiMiddleware                 │
│       └─ FastMCP StarletteWithLifespan              │
│           ├─ POST /mcp  →  tool execution           │
│           └─ GET  /mcp  →  SSE event stream         │
│                                                     │
│  panther_mcp_app.py                                 │
│   └─ FastMCP server (singleton per worker process)  │
│       ├─ All Panther tools   (list_alerts, etc.)    │
│       ├─ All Panther prompts (alert_triage, etc.)   │
│       └─ All Panther resources (config://panther)   │
└─────────────────────────────────────────────────────┘
        │
        │  GraphQL / REST  (aiohttp connection pool)
        ▼
  Panther SIEM API
```

---

## Files

| File | Purpose |
|------|---------|
| `function_app.py` | Azure Functions v2 entry point; wraps FastMCP with `AsgiMiddleware` |
| `panther_mcp_app.py` | FastMCP server factory; creates singleton and returns ASGI app |
| `host.json` | Azure Functions host config (timeouts, concurrency, route prefix) |
| `local.settings.json.template` | Template for local dev env vars – **copy, rename, fill in secrets** |
| `requirements.txt` | Python dependencies for the Function App |
| `.funcignore` | Files excluded from `az functionapp deployment` package |

---

## Prerequisites

| Tool | Install |
|------|---------|
| Python 3.12+ | https://python.org |
| Azure CLI | `brew install azure-cli` / [docs](https://docs.microsoft.com/cli/azure/install-azure-cli) |
| Azure Functions Core Tools v4 | `npm install -g azure-functions-core-tools@4` |
| `uv` (optional but recommended) | `curl -Lsf https://astral.sh/uv/install.sh \| sh` |

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PANTHER_INSTANCE_URL` | **Yes** | Base URL of your Panther instance (e.g. `https://tenant.runpanther.io`) |
| `PANTHER_API_TOKEN` | **Yes** | API token with appropriate Panther permissions |
| `STATELESS_HTTP` | No | `"true"` to enable stateless MCP mode (recommended for Consumption plan). Default: `"false"` |
| `LOG_LEVEL` | No | Python log level: `DEBUG`, `INFO`, `WARNING`, `ERROR`. Default: `WARNING` |
| `PANTHER_ALLOW_INSECURE_INSTANCE` | No | `"true"` to disable TLS verification (testing only) |

---

## Local Development

### 1. Copy and configure settings

```bash
cd azure_streaming_mcp
cp local.settings.json.template local.settings.json
# Edit local.settings.json and fill in your PANTHER_INSTANCE_URL and PANTHER_API_TOKEN
```

> **Never commit `local.settings.json`** – it is git-ignored by `.funcignore` and
> should be treated as a secret file.

### 2. Install the mcp-panther package

The Azure Functions app imports from `mcp_panther`; during local dev the
easiest way to make it available is an editable install from the repo root:

```bash
# From the repo root
pip install -e .
# or with uv:
uv sync
```

### 3. Install Azure Functions dependencies

```bash
pip install -r azure_streaming_mcp/requirements.txt
# or:
uv pip install -r azure_streaming_mcp/requirements.txt
```

### 4. Run locally with Azure Functions Core Tools

```bash
cd azure_streaming_mcp
func start
```

The MCP endpoint will be available at:

```
http://localhost:7071/mcp
```

### 5. Validate with the test client

```bash
# From the repo root, in a second terminal:
uv run python local_streaming_mcp/test_streaming_client.py \
  --url http://localhost:7071 \
  --verbose
```

---

## Deploying to Azure

### Step 1 – Create Azure resources

```bash
# Variables – change these to your preferences
RESOURCE_GROUP=rg-panther-mcp
LOCATION=eastus
STORAGE_ACCOUNT=stpanthermcp$RANDOM
FUNCTION_APP=panther-mcp-$RANDOM

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create storage account (required by Azure Functions)
az storage account create \
  --name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS

# Create the Function App (Python 3.12, Linux)
az functionapp create \
  --resource-group $RESOURCE_GROUP \
  --consumption-plan-location $LOCATION \
  --runtime python \
  --runtime-version 3.12 \
  --functions-version 4 \
  --name $FUNCTION_APP \
  --storage-account $STORAGE_ACCOUNT \
  --os-type Linux
```

### Step 2 – Configure application settings

```bash
az functionapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $FUNCTION_APP \
  --settings \
    PANTHER_INSTANCE_URL="https://your-tenant.runpanther.io" \
    PANTHER_API_TOKEN="your-api-token" \
    STATELESS_HTTP="true" \
    LOG_LEVEL="WARNING"
```

> **Security tip**: Store `PANTHER_API_TOKEN` in Azure Key Vault and reference
> it as a Key Vault secret reference:
> `@Microsoft.KeyVault(SecretUri=https://your-kv.vault.azure.net/secrets/PantherApiToken/)`

### Step 3 – Deploy the function code

```bash
cd azure_streaming_mcp

# Option A: Publish directly (installs mcp-panther from PyPI)
func azure functionapp publish $FUNCTION_APP --python

# Option B: Build and publish a container (for Premium/Dedicated plans)
# See Dockerfile section below.
```

### Step 4 – Get the MCP endpoint URL

```bash
FUNCTION_URL=$(az functionapp show \
  --resource-group $RESOURCE_GROUP \
  --name $FUNCTION_APP \
  --query "defaultHostName" -o tsv)

echo "MCP endpoint: https://$FUNCTION_URL/mcp"
```

### Step 5 – Configure your MCP client

**Claude Code:**
```bash
claude mcp add-json panther-azure '{
  "url": "https://YOUR-FUNCTION-APP.azurewebsites.net/mcp"
}'
```

**Claude Desktop / Cursor (add to config JSON):**
```json
{
  "mcpServers": {
    "panther-azure": {
      "url": "https://YOUR-FUNCTION-APP.azurewebsites.net/mcp"
    }
  }
}
```

---

## Streaming Behaviour

### How MCP Streamable-HTTP works

The MCP Streamable-HTTP transport uses two HTTP interactions:

1. **POST `/mcp`** – the MCP client sends a JSON-RPC request body.
   The server can respond with:
   - `Content-Type: application/json` – a single, non-streamed response.
   - `Content-Type: text/event-stream` – a Server-Sent Events (SSE) stream
     of one or more JSON-RPC responses, allowing incremental delivery.

2. **GET `/mcp`** – the client opens a persistent SSE channel to receive
   server-initiated notifications (e.g. progress updates, log messages).

### Azure Functions constraints

| Plan | SSE support | Max timeout | Notes |
|------|-------------|-------------|-------|
| **Consumption** | Limited | 10 min | Set `STATELESS_HTTP=true`; each POST is independent |
| **Flex Consumption** | Better | 30 min | Supports longer SSE sessions |
| **Premium (EP)** | Full | Unlimited* | Set `WEBSITE_SOCKET_TIMEOUT` as needed |
| **Dedicated (App Service)** | Full | Unlimited* | Best for production SSE streaming |

> *Subject to Azure front-door and load-balancer idle timeouts (~230 s by default).
> Set `WEBSITE_HTTPSCALEV2_ENABLED=0` and tune `WEBSITE_SOCKET_TIMEOUT` on
> Premium/Dedicated plans for long-lived SSE connections.

### Stateless vs stateful mode

| Mode | `STATELESS_HTTP` | Behaviour |
|------|-----------------|-----------|
| **Stateless** | `true` | Each POST request is handled independently; no persistent SSE session. Best for Consumption plan. |
| **Stateful** | `false` (default) | Server maintains an SSE session per client; supports server-initiated messages. Requires Premium or Dedicated plan. |

---

## Container Deployment (Premium / Dedicated Plans)

For production SSE streaming without timeout limits, deploy as a container:

```dockerfile
# Dockerfile (in azure_streaming_mcp/)
FROM mcr.microsoft.com/azure-functions/python:4-python3.12

WORKDIR /home/site/wwwroot

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install mcp-panther from the repo
COPY ../src /tmp/mcp_panther_src
RUN pip install --no-cache-dir /tmp/mcp_panther_src

# Copy function code
COPY . .

ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true
```

```bash
# Build and push to Azure Container Registry
ACR_NAME=your-acr-name

az acr build \
  --registry $ACR_NAME \
  --image panther-mcp-azure:latest \
  azure_streaming_mcp/

az functionapp create \
  --resource-group $RESOURCE_GROUP \
  --plan your-premium-plan \
  --name $FUNCTION_APP \
  --deployment-container-image-name $ACR_NAME.azurecr.io/panther-mcp-azure:latest \
  --functions-version 4
```

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'mcp_panther'`

The `mcp_panther` package is not installed.  Options:
1. Add `mcp-panther==<version>` to `requirements.txt` (uses PyPI version).
2. Run `pip install -e <repo_root>` before `func start`.
3. Use the container deployment which copies the source.

### `Error: 403 Forbidden` on tool call

The `PANTHER_API_TOKEN` lacks the permission required by that tool.
Check the tool's `Permissions:` annotation in the tool description.

### SSE connection drops immediately on Consumption plan

Set `STATELESS_HTTP=true`.  The Consumption plan's proxy infrastructure
does not support long-lived HTTP connections.

### `azure.functions.AsgiMiddleware` not found

Upgrade `azure-functions` to >= 1.18.0:
```bash
pip install "azure-functions>=1.18.0"
```

### Function times out before tool responds

Increase `functionTimeout` in `host.json` (max `00:10:00` on Consumption,
unlimited on Premium/Dedicated) or switch to a higher-tier plan.

---

## Security Recommendations

- Store `PANTHER_API_TOKEN` in **Azure Key Vault** and reference it via a
  Key Vault reference in App Settings.
- Enable **Azure Functions authentication** (Easy Auth) if the MCP endpoint
  should be restricted to specific clients.
- Use **VNET integration** to keep traffic between the Function App and your
  Panther instance off the public internet.
- Rotate the API token regularly and bind it to the Function App's outbound
  IP addresses in Panther's token settings.
