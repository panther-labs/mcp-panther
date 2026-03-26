# Deploying mcp-panther to Azure Functions (Self-Hosted)

This guide covers deploying mcp-panther as a remote MCP server on Azure Functions using the [self-hosted custom handler approach](https://learn.microsoft.com/en-us/azure/azure-functions/self-hosted-mcp-servers). No code changes to the server are required — only the configuration files in this repository are needed.

## How It Works

Azure Functions acts as a reverse proxy via the **custom handler** mechanism:

```
MCP Client → Azure Functions host (HTTPS) → startup.sh → mcp-panther (streamable-http on port 8080)
```

The `mcp-custom-handler` configuration profile in `host.json` automatically:
- Enables HTTP proxying (`enableProxying: true`) so the full request is forwarded to the server
- Sets a wildcard route (`{*route}`) so all paths (including `/mcp`) are forwarded
- Removes the default `/api` route prefix so the MCP endpoint is at the root

## Prerequisites

### Azure CLI

| OS | Install |
|---|---|
| macOS | `brew install azure-cli` |
| Linux | `curl -sL https://aka.ms/InstallAzureCLIDeb \| sudo bash` |
| Windows | `winget install Microsoft.AzureCLI` |

### Azure Functions Core Tools v4

| OS | Install |
|---|---|
| macOS | `brew tap azure/functions && brew install azure-functions-core-tools@4` |
| Linux (Ubuntu/Debian) | See [Linux install instructions](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local#linux) |
| Windows | `winget install Microsoft.AzureFunctionsCoreTools` |

### Python 3.12+

| OS | Install |
|---|---|
| macOS | `brew install python@3.12` |
| Linux (Ubuntu/Debian) | `sudo apt install python3.12 python3.12-venv` |
| Windows | `winget install Python.Python.3.12` |

### uv

| OS | Install |
|---|---|
| macOS / Linux | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Windows (PowerShell) | `powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 \| iex"` |

> **Windows note:** `startup.sh` uses bash. For local development on Windows you need either
> [Git Bash](https://git-scm.com/downloads) (recommended) or
> [WSL 2](https://learn.microsoft.com/en-us/windows/wsl/install).
> On Azure, the Functions host runs on Linux so `startup.sh` works without any extra setup.

---

## Local Development

Test the Azure Functions setup locally before deploying to Azure using Azure Functions Core Tools, which simulates the Functions host and the custom handler proxy.

### 1. Install dependencies

```bash
# macOS / Linux / Windows (Git Bash)
uv sync
```

### 2. Configure credentials

`local.settings.json` is gitignored and not included in the repository — you need to create it in the project root yourself. Copy the template below into a new file named `local.settings.json` and fill in your Panther credentials:

**macOS / Linux**
```bash
cat > local.settings.json << 'EOF'
{
    "IsEncrypted": false,
    "Values": {
        "FUNCTIONS_WORKER_RUNTIME": "custom",
        "PANTHER_INSTANCE_URL": "https://YOUR-INSTANCE.panther.io",
        "PANTHER_API_TOKEN": "YOUR-API-TOKEN",
        "LOG_LEVEL": "INFO"
    }
}
EOF
```

**Windows (PowerShell)**
```powershell
@"
{
    "IsEncrypted": false,
    "Values": {
        "FUNCTIONS_WORKER_RUNTIME": "custom",
        "PANTHER_INSTANCE_URL": "https://YOUR-INSTANCE.panther.io",
        "PANTHER_API_TOKEN": "YOUR-API-TOKEN",
        "LOG_LEVEL": "INFO"
    }
}
"@ | Set-Content local.settings.json
```

Replace `YOUR-INSTANCE.panther.io` and `YOUR-API-TOKEN` with your actual values.

> **Important:** `local.settings.json` is gitignored — never commit it. It contains your API token in plain text.

### 3. Activate the virtual environment

**macOS / Linux**
```bash
source .venv/bin/activate
```

**Windows (PowerShell)**
```powershell
.venv\Scripts\Activate.ps1
```

**Windows (Git Bash)**
```bash
source .venv/Scripts/activate
```

### 4. Start the local Functions host

**macOS / Linux / Windows (Git Bash)**
```bash
func start
```

**Windows (PowerShell)**
```powershell
func start
```

The Functions host starts on `http://localhost:7071` and launches `startup.sh`, which installs the package and starts the MCP server on port 8080. The Functions host proxies all traffic to it.

Expected output:
```
Azure Functions Core Tools
Core Tools Version: 4.x.x
...
[startup.sh] Installing mcp-panther...
[startup.sh] Starting Panther MCP server on port 8080...
...
Functions:
    custom-handler: [GET,POST] http://localhost:7071/{*route}
```

### 5. Connect an MCP client locally

#### Claude Code

Native HTTP support — no proxy needed:

```bash
claude mcp add-json panther-local '{"url": "http://localhost:7071/mcp"}'
```

#### Claude Desktop

Claude Desktop only supports STDIO transport. Use [`mcp-remote`](https://www.npmjs.com/package/mcp-remote) as a bridge (requires Node.js):

```json
{
    "mcpServers": {
        "panther-local": {
            "command": "npx",
            "args": ["-y", "mcp-remote", "http://localhost:7071/mcp"]
        }
    }
}
```

#### Cursor

```json
{
    "mcpServers": {
        "panther-local": {
            "url": "http://localhost:7071/mcp"
        }
    }
}
```

> **Note:** `func start` is required for local testing — you cannot run `python -m mcp_panther.server` directly and have it work with the Functions proxy. If you need to test the server standalone without Functions, use `uv run python -m mcp_panther.server --transport streamable-http --host 127.0.0.1 --port 8080` instead.

---

## Azure Deployment

### Step 1: Log in and set subscription

**macOS / Linux / Windows**
```bash
az login
az account set --subscription "<YOUR-SUBSCRIPTION-ID>"
```

### Step 2: Create Azure resources

> **Required plan:** Flex Consumption — self-hosted MCP servers must be hosted on the Flex Consumption plan per the [Azure Functions MCP documentation](https://learn.microsoft.com/en-us/azure/azure-functions/self-hosted-mcp-servers).

**macOS / Linux / Windows (Git Bash)**
```bash
# Variables — adjust to your preference
RESOURCE_GROUP="rg-panther-mcp"
LOCATION="eastus2"
STORAGE_ACCOUNT="stpanthermcp$RANDOM"   # must be globally unique
FUNCTION_APP="panther-mcp-$RANDOM"      # must be globally unique

# Resource group
az group create \
    --name "$RESOURCE_GROUP" \
    --location "$LOCATION"

# Storage account (required by Functions)
az storage account create \
    --name "$STORAGE_ACCOUNT" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --sku Standard_LRS

# Function App on Flex Consumption plan
az functionapp create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$FUNCTION_APP" \
    --storage-account "$STORAGE_ACCOUNT" \
    --flexconsumption-location "$LOCATION" \
    --runtime python \
    --runtime-version 3.12
```

**Windows (PowerShell)**
```powershell
# Variables — adjust to your preference
$RESOURCE_GROUP = "rg-panther-mcp"
$LOCATION = "eastus2"
$STORAGE_ACCOUNT = "stpanthermcp$(Get-Random -Maximum 99999)"   # must be globally unique
$FUNCTION_APP = "panther-mcp-$(Get-Random -Maximum 99999)"      # must be globally unique

# Resource group
az group create `
    --name $RESOURCE_GROUP `
    --location $LOCATION

# Storage account (required by Functions)
az storage account create `
    --name $STORAGE_ACCOUNT `
    --resource-group $RESOURCE_GROUP `
    --location $LOCATION `
    --sku Standard_LRS

# Function App on Flex Consumption plan
az functionapp create `
    --resource-group $RESOURCE_GROUP `
    --name $FUNCTION_APP `
    --storage-account $STORAGE_ACCOUNT `
    --flexconsumption-location $LOCATION `
    --runtime python `
    --runtime-version 3.12
```

### Step 3: Configure application settings

**macOS / Linux / Windows (Git Bash)**
```bash
az functionapp config appsettings set \
    --resource-group "$RESOURCE_GROUP" \
    --name "$FUNCTION_APP" \
    --settings \
        FUNCTIONS_WORKER_RUNTIME=custom \
        PANTHER_INSTANCE_URL="https://YOUR-INSTANCE.panther.io" \
        PANTHER_API_TOKEN="YOUR-API-TOKEN" \
        LOG_LEVEL="WARNING"
```

**Windows (PowerShell)**
```powershell
az functionapp config appsettings set `
    --resource-group $RESOURCE_GROUP `
    --name $FUNCTION_APP `
    --settings `
        FUNCTIONS_WORKER_RUNTIME=custom `
        PANTHER_INSTANCE_URL="https://YOUR-INSTANCE.panther.io" `
        PANTHER_API_TOKEN="YOUR-API-TOKEN" `
        LOG_LEVEL="WARNING"
```

> **Security tip:** Use Azure Key Vault references instead of plain-text values for secrets:
> ```
> PANTHER_API_TOKEN="@Microsoft.KeyVault(SecretUri=https://YOUR-VAULT.vault.azure.net/secrets/panther-api-token/)"
> ```

### Step 4: Deploy the function app

**macOS / Linux / Windows (Git Bash)**
```bash
func azure functionapp publish "$FUNCTION_APP"
```

**Windows (PowerShell)**
```powershell
func azure functionapp publish $FUNCTION_APP
```

`startup.sh` runs on first request and installs the package. Subsequent cold starts reuse the cached installation.

### Step 5: Verify deployment

**macOS / Linux / Windows (Git Bash)**
```bash
# Check the function app is running
az functionapp show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$FUNCTION_APP" \
    --query "state" -o tsv

# Test the MCP endpoint
curl -s "https://${FUNCTION_APP}.azurewebsites.net/mcp"
```

**Windows (PowerShell)**
```powershell
# Check the function app is running
az functionapp show `
    --resource-group $RESOURCE_GROUP `
    --name $FUNCTION_APP `
    --query "state" -o tsv

# Test the MCP endpoint
Invoke-RestMethod -Uri "https://$FUNCTION_APP.azurewebsites.net/mcp"
```

---

## Connecting MCP Clients to the Remote Server

### Claude Code

Native HTTP support — no proxy needed:

```bash
claude mcp add-json panther '{
    "url": "https://YOUR-FUNCTION-APP.azurewebsites.net/mcp"
}'
```

### Claude Desktop

Claude Desktop only supports STDIO transport. Use [`mcp-remote`](https://www.npmjs.com/package/mcp-remote) as a bridge (requires Node.js):

```json
{
    "mcpServers": {
        "panther": {
            "command": "npx",
            "args": ["-y", "mcp-remote", "https://YOUR-FUNCTION-APP.azurewebsites.net/mcp"]
        }
    }
}
```

### Cursor

```json
{
    "mcpServers": {
        "panther": {
            "url": "https://YOUR-FUNCTION-APP.azurewebsites.net/mcp"
        }
    }
}
```

---

## Authentication (Recommended for Production)

By default the endpoint is publicly accessible. Azure Functions provides two options to secure it.

### Option A: Built-in App Service Authentication (OAuth / Entra ID)

This satisfies the MCP authorization spec (issues 401 challenges, exposes Protected Resource Metadata). Configure it in the Azure portal:

1. Navigate to your Function App → **Authentication**
2. Click **Add identity provider** → Select **Microsoft**
3. Configure the app registration (or let Azure create one)
4. Set **Unauthenticated requests** to `HTTP 401 Unauthorized`

Clients must obtain an Entra ID token and pass it as a bearer token:
```
Authorization: Bearer <token>
```

### Option B: Function-level API Keys

Set `defaultAuthorizationLevel` in `host.json` and pass the key as a query parameter:

```json
{
    "version": "2.0",
    "configurationProfile": "mcp-custom-handler",
    "customHandler": {
        "description": {
            "defaultExecutablePath": "bash",
            "arguments": ["startup.sh"]
        },
        "port": "8080",
        "http": {
            "defaultAuthorizationLevel": "function"
        }
    }
}
```

**macOS / Linux / Windows (Git Bash)**
```bash
az functionapp keys list \
    --resource-group "$RESOURCE_GROUP" \
    --name "$FUNCTION_APP"
```

**Windows (PowerShell)**
```powershell
az functionapp keys list `
    --resource-group $RESOURCE_GROUP `
    --name $FUNCTION_APP
```

MCP client URL with key:
```
https://YOUR-FUNCTION-APP.azurewebsites.net/mcp?code=YOUR-FUNCTION-KEY
```

---

## Troubleshooting

### `$'\r': command not found` or `pip: command not found` on Windows

This is caused by two separate Windows issues that the current `startup.sh` handles automatically — but only if your checkout has LF line endings.

**Root cause 1 — CRLF line endings:** Windows Git converts `\n` to `\r\n` on checkout when `core.autocrlf=true`. Bash then sees `\r` as a command on every line. The repo contains a `.gitattributes` rule that forces LF for `startup.sh`, but if you cloned before this fix was added, your local copy may still have CRLF.

Fix: re-checkout the file to apply the `.gitattributes` rule:

```powershell
# In PowerShell or Git Bash
git checkout startup.sh
```

Verify the line endings are LF:
```bash
file startup.sh   # should NOT say "CRLF"
```

**Root cause 2 — venv not active in bash:** Even if you ran `.venv\Scripts\Activate.ps1` in PowerShell, the bash subprocess started by `func` gets its own environment. `startup.sh` now detects and activates the venv itself, so you no longer need to activate before running `func start`.

### `func start` fails to find `python`

Ensure the virtual environment was created first:

```bash
# macOS / Linux / Windows (Git Bash or PowerShell)
uv sync
func start
```

`startup.sh` will activate the venv automatically. Manual activation before `func start` is no longer required.

### `startup.sh` not found or permission denied on Windows (local)

`startup.sh` requires bash. Install [Git for Windows](https://git-scm.com/downloads) (includes Git Bash) and ensure `bash` is on your `PATH`, or use WSL 2. Verify with:

```bash
bash --version
```

### `startup.sh` permission denied on Azure

The deployment zip must preserve the executable bit. Check it with:

```bash
# macOS / Linux / Windows (Git Bash)
ls -la startup.sh  # should show -rwxr-xr-x
```

If lost, re-add it before deploying:

```bash
chmod +x startup.sh
```

### MCP client receives `404` or empty response

Verify the route prefix is empty. The `mcp-custom-handler` profile sets this automatically, but if you have a custom `host.json`, confirm `extensions.http.routePrefix` is `""`.

### Cold start is slow

`startup.sh` runs `pip install .` on every new instance cold start. To speed this up in CI/CD, pre-install dependencies before deploying.

**macOS / Linux / Windows (Git Bash)**
```bash
# Pre-install dependencies into a local target directory
pip install -r requirements.txt --target .python_packages/lib/site-packages

# Update startup.sh to use pre-installed packages instead of running pip install:
export PYTHONPATH=".python_packages/lib/site-packages:${PYTHONPATH}"
exec python -m mcp_panther.server --transport streamable-http --host 0.0.0.0 --port 8080
```

**Windows (PowerShell)**
```powershell
# Pre-install dependencies into a local target directory
pip install -r requirements.txt --target .python_packages/lib/site-packages
```

### View server logs

**macOS / Linux / Windows (Git Bash)**
```bash
# Stream live logs from Azure
func azure functionapp logstream "$FUNCTION_APP"

# Or via Azure CLI
az webapp log tail \
    --resource-group "$RESOURCE_GROUP" \
    --name "$FUNCTION_APP"
```

**Windows (PowerShell)**
```powershell
func azure functionapp logstream $FUNCTION_APP

az webapp log tail `
    --resource-group $RESOURCE_GROUP `
    --name $FUNCTION_APP
```

---

## Azure API Center Registration (Optional)

Register the deployed server in Azure API Center to share it across your organization:

**macOS / Linux / Windows (Git Bash)**
```bash
az apic api register \
    --resource-group "$RESOURCE_GROUP" \
    --service-name "<YOUR-API-CENTER>" \
    --api-location "https://${FUNCTION_APP}.azurewebsites.net/mcp"
```

**Windows (PowerShell)**
```powershell
az apic api register `
    --resource-group $RESOURCE_GROUP `
    --service-name "<YOUR-API-CENTER>" `
    --api-location "https://$FUNCTION_APP.azurewebsites.net/mcp"
```

See [Register MCP servers in Azure API Center](https://learn.microsoft.com/en-us/azure/api-center/register-mcp-servers) for full details.
