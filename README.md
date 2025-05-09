# Panther MCP Server

[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Panther's Model Context Protocol (MCP) server provides functionality to:
1. **Write and tune detections from your IDE**
2. **Interactively query security logs using natural language**
3. **Triage, comment, and resolve one or many alerts**

## Available Tools

<details>
<summary><strong>Alerts</strong></summary>

| Tool Name | Description | Sample Prompt |
|-----------|-------------|---------------|
| `add_alert_comment` | Add a comment to a Panther alert | "Add comment 'Looks pretty bad' to alert abc123" |
| `get_alert_by_id` | Get detailed information about a specific alert | "What's the status of alert 8def456?" |
| `get_alert_events` | Get a small sampling of events for a given alert | "Show me events associated with alert 8def456" |
| `list_alerts` | List alerts with comprehensive filtering options (date range, severity, status, etc.) | "Show me all high severity alerts from the last 24 hours" |
| `update_alert_assignee_by_id` | Update the assignee of one or more alerts | "Assign alerts abc123 and def456 to John" |
| `update_alert_status` | Update the status of one or more alerts | "Mark alerts abc123 and def456 as resolved" |

</details>

<details>
<summary><strong>Data</strong></summary>

| Tool Name | Description | Sample Prompt |
|-----------|-------------|---------------|
| `execute_data_lake_query` | Execute SQL queries against Panther's data lake | "Query AWS CloudTrail logs for failed login attempts in the last day" |
| `get_data_lake_query_results` | Get results from a previously executed data lake query | "Get results for query ID abc123" |
| `get_sample_log_events` | Get a sample of 10 recent events for a specific log type | "Show me sample events from AWS_CLOUDTRAIL logs" |
| `get_table_columns` | Get column details for a specific data lake table | "What columns exist within the table panther_logs.public.aws_cloudtrail" |
| `get_table_schema` | Get schema information for a specific table | "Show me the schema for the AWS_CLOUDTRAIL table" |
| `get_tables_for_database` | Get all tables for a specific data lake database | "What tables are within the panther_logs.public database" |
| `list_databases` | List all available data lake databases in Panther | "List all available databases" |
| `list_log_sources` | List log sources with optional filters (health status, log types, integration type) | "Show me all healthy S3 log sources" |
| `list_tables_for_database` | List all available tables for a specific database in Panther's data lake | "What tables are in the panther_logs database" |

</details>

<details>
<summary><strong>Rules</strong></summary>

| Tool Name | Description | Sample Prompt |
|-----------|-------------|---------------|
| `create_rule` | Create a new Panther rule | "Create a new rule to detect failed logins" |
| `disable_rule` | Disable a rule by setting enabled to false | "Disable rule abc123" |
| `get_global_helper_by_id` | Get detailed information about a specific global helper | "Get details for global helper ID panther_github_helpers" |
| `get_rule_by_id` | Get detailed information about a specific rule | "Get details for rule ID abc123" |
| `get_scheduled_rule_by_id` | Get detailed information about a specific scheduled rule | "Get details for scheduled rule abc123" |
| `get_simple_rule_by_id` | Get detailed information about a specific simple rule | "Get details for simple rule abc123" |
| `list_global_helpers` | List all Panther global helpers with optional pagination | "Show me all global helpers for CrowdStrike events" |
| `list_rules` | List all Panther rules with optional pagination | "Show me all enabled rules" |
| `list_scheduled_rules` | List all scheduled rules with optional pagination | "List all scheduled rules in Panther" |
| `list_simple_rules` | List all simple rules with optional pagination | "Show me all simple rules in Panther" |
| `put_rule` | Update an existing rule or create a new one | "Update rule abc123 with new severity HIGH" |

</details>

<details>
<summary><strong>Schemas</strong></summary>

| Tool Name | Description | Sample Prompt |
|-----------|-------------|---------------|
| `create_or_update_schema` | Create or update a schema | "Create a new schema for custom log type" |
| `get_schema_details` | Get detailed information for specific schemas | "Get full details for AWS.CloudTrail schema" |
| `list_schemas` | List available schemas with optional filters | "Show me all AWS-related schemas" |

</details>

<details>
<summary><strong>Metrics</strong></summary>

| Tool Name | Description | Sample Prompt |
|-----------|-------------|---------------|
| `get_metrics_alerts_per_rule` | Get metrics about alerts grouped by rule | "Show top 10 rules by alert count" |
| `get_metrics_alerts_per_severity` | Get metrics about alerts grouped by severity | "Show alert counts by severity for the last week" |

</details>

<details>
<summary><strong>Users</strong></summary>

| Tool Name | Description | Sample Prompt |
|-----------|-------------|---------------|
| `list_panther_users` | List all Panther user accounts | "Show me all active Panther users" |

</details>

## Security Best Practices

Panther highly recommends the following MCP best practices:

- **Run only trusted, officially signed MCP servers.** Verify digital signatures or checksums before running, audit the tool code, and avoid community tools from unofficial publishers.
- **Apply strict least-privilege to Panther API tokens.** Scope tokens to the minimal permissions required and bind them to an IP allow-list or CIDR range so they're useless if exfiltrated. Rotate credentials on a preferred interval (e.g., every 30d).
- **Host the MCP server in a locked-down sandbox (e.g., Docker) with read-only mounts.** This confines any compromise to a minimal blast radius.
- **Monitor credential access to Panther and monitor for anomalies.** Write a Panther rule!
- **Scan MCP servers with `mcp-scan`.** Utilize the `mcp-scan` tool by [invariantlabs](https://github.com/invariantlabs-ai/mcp-scan) for common vulnerabilities.

## Panther Configuration

1. Create an API token in Panther:
   - Navigate to Settings (gear icon) → API Tokens
   - Create a new token with the following permissions (recommended read-only approach to start):
   - <details>
     <summary><strong>View Required Permissions</strong></summary>

     ![Screenshot of Panther Token permissions](panther-token-perms-1.png)
     ![Screenshot of Panther Token permissions](panther-token-perms-2.png)

     </details>

2. Store the generated token securely (e.g., in 1Password)

3. Grab the Panther instance URL from your browser (e.g., `https://YOUR-PANTHER-INSTANCE.domain`)
    - Note: This must include `https://`

## MCP Installation

Clone this repository:
```bash
git clone git@github.com:panther-labs/mcp-panther.git
```

**Choose one of the following installation methods below.**

### Docker Setup
1. Ensure Docker is installed on your system
2. Build the Docker image:
```bash
make build-docker
```
3. Verify the image was built successfully:
```bash
docker images | grep mcp-panther
```
4. Configure your MCP client of choice (below):
```json
{
  "mcpServers": {
    "mcp-panther": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "-e", "PANTHER_INSTANCE_URL",
        "-e", "PANTHER_API_TOKEN",
        "--rm",
        "mcp-panther"
      ],
      "env": {
        "PANTHER_INSTANCE_URL": "https://YOUR-PANTHER-INSTANCE.domain",
        "PANTHER_API_TOKEN": "YOUR-API-KEY"
      }
    }
  }
}
```

### UV Setup
1. Ensure Python 3.12 is installed:
```bash
pyenv install 3.12  # if using pyenv
```

2. [Install UV](https://docs.astral.sh/uv/getting-started/installation/)

3. Create virtual environment and install dependencies:

#### macOS/Linux
```bash
uv venv
source .venv/bin/activate
uv sync
```

`uv synv` will install all dependencies from `requirements.txt` with exact versions.

#### Windows
```bash
uv venv
.venv\Scripts\activate
uv sync
```

4. Configure your MCP client of choice (below):
```json
{
  "mcpServers": {
    "mcp-panther": {
      "command": "uv",
      "args": [
        "run",
        "--with",
        "aiohttp",
        "--with",
        "gql[aiohttp]",
        "--with",
        "mcp[cli]",
        "mcp",
        "run",
        "FULL-PATH-TO-REPO/src/mcp_panther/server.py"
      ],
      "env": {
        "PANTHER_INSTANCE_URL": "https://YOUR-PANTHER-INSTANCE.domain",
        "PANTHER_API_TOKEN": "YOUR-PANTHER-API-TOKEN"
      }
    }
  }
}
```

## Client Setup

### Cursor
[Follow the instructions here](https://docs.cursor.com/context/model-context-protocol#configuring-mcp-servers) to configure your project or global MCP configuration. **It's VERY IMPORTANT that you do not check this file into version control.**

Once configured, navigate to Cursor Settings > MCP to view the running server:

<img src="panther-mcp-cursor-config.png" width="500" />

### Claude Desktop
Install the server directly:
```bash
uv run mcp install src/mcp_panther/server.py
```

If you run into any issues, [try the troubleshooting steps here](https://modelcontextprotocol.io/quickstart/user#troubleshooting).

### Goose
Use with [Goose](https://block.github.io/goose/), Block's open-source AI agent:
```bash
# Install the package with entry points
uv pip install .

# Start Goose with the MCP server
goose session --with-extension "uv run /path/to/mcp-panther/.venv/bin/mcp-panther"
```
> NOTE: Adjust the path to match your installation directory

## Troubleshooting

Check the server logs for detailed error messages: `tail -n 20 -F ~/Library/Logs/Claude/mcp*.log`. Common issues and solutions are listed below.

### Initializing mcp-panther

- If you see an error like `typer is required`, make sure you've installed MCP with CLI components: `pip install mcp[cli]`
- Ensure the `npm` and `uv` are installed **globally** on your system.

### Running tools

- If you get a `{"success": false, "message": "Failed to [action]: Request failed (HTTP 403): {\"error\": \"forbidden\"}"}` error, it likely means your API token lacks the particular permission needed by the tool.
- Ensure your Panther Instance URL is correctly set. You can view this in the `config://panther` resource from your MCP Client.

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.

## Contributing

We welcome contributions to improve MCP-Panther! Here's how you can help:

1. **Report Issues**: Open an issue for any bugs or feature requests
2. **Submit Pull Requests**: Fork the repository and submit PRs for bug fixes or new features
3. **Improve Documentation**: Help us make the documentation clearer and more comprehensive
4. **Share Use Cases**: Let us know how you're using MCP-Panther and what could make it better

Please ensure your contributions follow our coding standards and include appropriate tests and documentation.
