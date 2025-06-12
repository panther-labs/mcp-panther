# Panther MCP Server

[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Panther's Model Context Protocol (MCP) server provides functionality to:
1. **Write and tune detections from your IDE**
2. **Interactively query security logs using natural language**
3. **Triage, comment, and resolve one or many alerts**

<a href="https://glama.ai/mcp/servers/@panther-labs/mcp-panther">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/@panther-labs/mcp-panther/badge" alt="Panther Server MCP server" />
</a>

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
| `list_alert_comments` | List all comments for a specific alert | "Show me all comments for alert abc123" |

</details>

<details>
<summary><strong>Data</strong></summary>

| Tool Name | Description | Sample Prompt |
|-----------|-------------|---------------|
| `execute_data_lake_query` | Execute SQL queries against Panther's data lake | "Query AWS CloudTrail logs for failed login attempts in the last day" |
| `get_data_lake_query_results` | Get results from a previously executed data lake query | "Get results for query ID abc123" |
| `get_sample_log_events` | Get a sample of 10 recent events for a specific log type | "Show me sample events from AWS_CLOUDTRAIL logs" |
| `get_table_schema` | Get schema information for a specific table | "Show me the schema for the AWS_CLOUDTRAIL table" |
| `list_databases` | List all available data lake databases in Panther | "List all available databases" |
| `list_log_sources` | List log sources with optional filters (health status, log types, integration type) | "Show me all healthy S3 log sources" |
| `list_database_tables` | List all available tables for a specific database in Panther's data lake | "What tables are in the panther_logs database" |
| `summarize_alert_events` | Analyze patterns and relationships across multiple alerts by aggregating their event data | "Show me patterns in events from alerts abc123 and def456" |

</details>

<details>
<summary><strong>Rules</strong></summary>

| Tool Name | Description | Sample Prompt |
|-----------|-------------|---------------|
| `create_rule` | Create a new Panther rule | "Create a new rule to detect more than 7 failed logins within a day across any user in the AWS Console" |
| `disable_rule` | Disable a rule by setting enabled to false | "Disable rule abc123" |
| `get_global_helper_by_id` | Get detailed information about a specific global helper | "Get details for global helper ID panther_github_helpers" |
| `get_policy_by_id` | Get detailed information about a specific policy | "Get details for policy ID AWS.S3.Bucket.PublicReadACP" |
| `get_rule_by_id` | Get detailed information about a specific rule | "Get details for rule ID abc123" |
| `get_scheduled_rule_by_id` | Get detailed information about a specific scheduled rule | "Get details for scheduled rule abc123" |
| `get_simple_rule_by_id` | Get detailed information about a specific simple rule | "Get details for simple rule abc123" |
| `list_global_helpers` | List all Panther global helpers with optional pagination | "Show me all global helpers for CrowdStrike events" |
| `list_policies` | List all Panther policies with optional pagination | "Show me all policies for AWS resources" |
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
| `get_rule_alert_metrics` | Get metrics about alerts grouped by rule | "Show top 10 rules by alert count" |
| `get_severity_alert_metrics` | Get metrics about alerts grouped by severity | "Show alert counts by severity for the last week" |

</details>

<details>
<summary><strong>Users</strong></summary>

| Tool Name | Description | Sample Prompt |
|-----------|-------------|---------------|
| `list_panther_users` | List all Panther user accounts | "Show me all active Panther users" |
| `get_permissions` | Get the current user's permissions | "What permissions do I have?" |

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

     ![Screenshot of Panther Token permissions](.github/panther-token-perms-1.png)
     ![Screenshot of Panther Token permissions](.github/panther-token-perms-2.png)

     </details>

2. Store the generated token securely (e.g., in 1Password)

3. Grab the Panther instance URL from your browser (e.g., `https://YOUR-PANTHER-INSTANCE.domain`)
    - Note: This must include `https://`

## MCP Installation

**Choose one of the following installation methods:**

### Docker Setup (Recommended)
The easiest way to get started is using our pre-built Docker image:

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
        "ghcr.io/panther-labs/mcp-panther"
      ],
      "env": {
        "PANTHER_INSTANCE_URL": "https://YOUR-PANTHER-INSTANCE.domain",
        "PANTHER_API_TOKEN": "YOUR-API-KEY"
      }
    }
  }
}
```

### UVX Setup
For Python users, you can run directly from PyPI using uvx:

1. [Install UV](https://docs.astral.sh/uv/getting-started/installation/)

2. Configure your MCP client:
```json
{
  "mcpServers": {
    "mcp-panther": {
      "command": "uvx",
      "args": ["mcp-panther"],
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

<img src=".github/panther-mcp-cursor-config.png" width="500" />

**Tips:**
* Be specific about where you want to generate new rules by using the `@` symbol and then typing a specific directory.
* For more reliability during tool use, try selecting a specific model, like Claude 3.7 Sonnet.
* If your MCP Client is failing to find any tools from the Panther MCP Server, try restarting the Client and ensuring the MCP server is running. In Cursor, refresh the MCP Server and start a new chat.

### Claude Desktop
To use with Claude Desktop, manually configure your `claude_desktop_config.json`:

1. Open the Claude Desktop settings and navigate to the Developer tab
2. Click "Edit Config" to open the configuration file
3. Add the following configuration:

```json
{
  "mcpServers": {
    "mcp-panther": {
      "command": "uvx",
      "args": ["mcp-panther"],
      "env": {
        "PANTHER_INSTANCE_URL": "https://YOUR-PANTHER-INSTANCE.domain",
        "PANTHER_API_TOKEN": "YOUR-PANTHER-API-TOKEN"
      }
    }
  }
}
```

4. Save the file and restart Claude Desktop

If you run into any issues, [try the troubleshooting steps here](https://modelcontextprotocol.io/quickstart/user#troubleshooting).

### Goose
Use with [Goose](https://block.github.io/goose/), Block's open-source AI agent:
```bash
# Start Goose with the MCP server
goose session --with-extension "uvx mcp-panther"
```

## Troubleshooting

Check the server logs for detailed error messages: `tail -n 20 -F ~/Library/Logs/Claude/mcp*.log`. Common issues and solutions are listed below.

### Running tools

- If you get a `{"success": false, "message": "Failed to [action]: Request failed (HTTP 403): {\"error\": \"forbidden\"}"}` error, it likely means your API token lacks the particular permission needed by the tool.
- Ensure your Panther Instance URL is correctly set. You can view this in the `config://panther` resource from your MCP Client.

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.

## Contributors

This project exists thanks to all the people who contribute. Special thanks to [Tomasz Tchorz](https://github.com/tomasz-sq) and [Glenn Edwards](https://github.com/glenn-sq) from [Block](https://block.xyz), who played a core role in launching MCP-Panther as a joint open-source effort with Panther.

See our [CONTRIBUTORS.md](.github/CONTRIBUTORS.md) for a complete list of contributors.

## Contributing

We welcome contributions to improve MCP-Panther! Here's how you can help:

1. **Report Issues**: Open an issue for any bugs or feature requests
2. **Submit Pull Requests**: Fork the repository and submit PRs for bug fixes or new features
3. **Improve Documentation**: Help us make the documentation clearer and more comprehensive
4. **Share Use Cases**: Let us know how you're using MCP-Panther and what could make it better

Please ensure your contributions follow our coding standards and include appropriate tests and documentation.