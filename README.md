# Panther MCP Server

> Note: MCP-PANTHER IS IN ACTIVE DEVELOPMENT! We recommend careful considerations for expensive operations such as data lake queries.

[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

This is a Model Context Protocol (MCP) server for Panther that provides functionality to:
1. Authenticate with Panther using a Panther API key
2. Connect to Panther via GraphQL and list alerts from today
3. List and manage Panther rules
4. Query Panther's data lake
5. Monitor log sources

## Prerequisites

- Python 3.12
- Panther API key
- MCP client (like Claude Desktop App) to interact with the server

## Installation

1. Clone this repository or download the files.

2. Install the required dependencies:

**Using pip**

```bash
pip install .
```

**Using uv (recommended)**

On Unix/macOS:

```bash
uv venv
source .venv/bin/activate
uv sync
```

On Windows:

```bash
.venv\Scripts\activate
uv sync
```

This will install MCP with CLI components, which are necessary for the `mcp install` and `mcp dev` commands.

## Configuration

Create your API Token on the `/settings/api/tokens/` page (with least privilege) in your Panther instance along with copying the API URL.

Use the command, args, and env variables below:

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
        "--with",
        "python-dotenv",
        "mcp",
        "run",
        "PATH/TO/MCPS/mcp-panther/src/mcp_panther/server.py"
      ],
      "env": {
        "PANTHER_INSTANCE_URL": "https://YOUR-PANTHER-INSTANCE.domain",
        "PANTHER_API_KEY": "YOUR-API-KEY"
      }
    }
  }
}
```

### Credentials

Your Panther API key and URL can be configured in two ways:

1. Through the MCP Client configuration's `env` key (as shown in the Configuration section above). This will take the highest precedence.

2. Using a `.env` file in the root repository directory with the following format:

```
PANTHER_INSTANCE_URL=https://YOUR-PANTHER-INSTANCE.domain
PANTHER_API_KEY=YOUR-API-KEY
```

Make sure to replace the placeholder values with your actual Panther instance URLs and API key.

## Usage

### Option 1: Install in Claude Desktop App

The simplest way to use this server is to install it in the Claude Desktop App:

```bash
uv run mcp install src/mcp_panther/server.py
```

This will make the Panther MCP server available to Claude directly.

### Option 2: Run the Development Server

For testing and development, you can run the MCP server in development mode:

```bash
uv run mcp dev src/mcp_panther/server.py
```

This starts the MCP Inspector server and provides an interactive web interface to test its functionality.

### Option 3: Run as a Standalone Server

You can also run the server directly:

```bash
uv run python -m mcp_panther.server
```

This will start the server at http://127.0.0.1:8000/

## Available Tools

The server provides tools organized by common SIEM workflows:

| Category | Tool Name | Description | Sample Prompt |
|----------|-----------|-------------|---------------|
| **Alert Management** | | | |
| | `list_alerts` | List alerts with comprehensive filtering options (date range, severity, status, etc.) | "Show me all high severity alerts from the last 24 hours" |
| | `get_alert_by_id` | Get detailed information about a specific alert | "What's the status of alert 8def456?" |
| | `update_alert_status` | Update the status of one or more alerts | "Mark alerts abc123 and def456 as resolved" |
| | `add_alert_comment` | Add a comment to a Panther alert | "Add comment 'Looks pretty bad' to alert abc123" |
| | `update_alert_assignee_by_id` | Update the assignee of one or more alerts | "Assign alerts abc123 and def456 to John" |
| **Data Investigation** | | | |
| | `execute_data_lake_query` | Execute SQL queries against Panther's data lake | "Query AWS CloudTrail logs for failed login attempts in the last day" |
| | `get_data_lake_query_results` | Get results from a previously executed data lake query | "Get results for query ID abc123" |
| | `list_log_sources` | List log sources with optional filters (health status, log types, integration type) | "Show me all healthy S3 log sources" |
| | `get_table_schema` | Get schema information for a specific table | "Show me the schema for the AWS_CLOUDTRAIL table" |
| | `get_data_lake_dbs_tables_columns` | List databases, tables, and columns in the data lake | "List all available tables in the panther_logs database" |
| **Global Helpers** | | | |
| | `get_global_helper_by_id` | Get detailed information about a specific global helper | "Get details for global helper ID panther_github_helpers" |
| | `list_global_helpers` | List all Panther global helpers with optional pagination | "Show me all global helpers for CrowdStrike events" |
| **Rule Management** | | | |
| | `list_rules` | List all Panther rules with optional pagination | "Show me all enabled rules" |
| | `get_rule_by_id` | Get detailed information about a specific rule | "Get details for rule ID abc123" |
| | `list_scheduled_rules` | List all scheduled rules with optional pagination | "List all scheduled rules in Panther" |
| | `get_scheduled_rule_by_id` | Get detailed information about a specific scheduled rule | "Get details for scheduled rule abc123" |
| | `list_simple_rules` | List all simple rules with optional pagination | "Show me all simple rules in Panther" |
| | `get_simple_rule_by_id` | Get detailed information about a specific simple rule | "Get details for simple rule abc123" |
| | `create_rule` | Create a new Panther rule | "Create a new rule to detect failed logins" |
| | `put_rule` | Update an existing rule or create a new one | "Update rule abc123 with new severity HIGH" |
| | `disable_rule` | Disable a rule by setting enabled to false | "Disable rule abc123" |
| **Schema Management** | | | |
| | `list_schemas` | List available schemas with optional filters | "Show me all AWS-related schemas" |
| | `get_schema_details` | Get detailed information for specific schemas | "Get full details for AWS.CloudTrail schema" |
| | `create_or_update_schema` | Create or update a schema | "Create a new schema for custom log type" |
| **Analytics and Reporting** | | | |
| | `get_metrics_alerts_per_severity` | Get metrics about alerts grouped by severity | "Show alert counts by severity for the last week" |
| | `get_metrics_alerts_per_rule` | Get metrics about alerts grouped by rule | "Show top 10 rules by alert count" |
| **User Management** | | | |
| | `list_panther_users` | List all Panther user accounts | "Show me all active Panther users" |

## Available Resources

The server provides the following resources:

1. `config://panther`: Provides configuration information about the Panther API.

## Available Prompts

The server provides the following prompts:

1. `triage_alert`: Helps triage a specific alert by analyzing its details and associated events
2. `prioritize_and_triage_alerts`: Helps prioritize alerts based on severity, impact, and related events

## Troubleshooting

- If you encounter authentication errors, make sure your Panther API key is correct and has the necessary permissions.
- Check the server logs for detailed error messages: `tail -n 20 -F ~/Library/Logs/Claude/mcp*.log`
- Ensure your Panther API URLs are correctly set if you're using a custom Panther instance.
- If you see an error like `typer is required`, make sure you've installed MCP with CLI components: `pip install mcp[cli]`
- Ensure you have `npm` and `uv` installed globally on your system.

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.
