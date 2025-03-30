# Panther MCP Server

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

```bash
# Using pip
pip install -r requirements.txt

# Using uv (recommended)
uv venv
source .venv/bin/activate  # On Unix/macOS

# or
.venv\Scripts\activate  # On Windows
uv pip install -r requirements.txt
```

This will install MCP with CLI components, which are necessary for the `mcp install` and `mcp dev` commands.

3. Create a `.env` file in the same directory with your Panther API key and URLs:

```
# Panther API key for authentication
# You can get this from your Panther dashboard
PANTHER_API_KEY=your_panther_api_key_here

# Panther GraphQL API URL
# Only change this if you're using a custom Panther instance
PANTHER_GQL_API_URL=https://api.runpanther.com/public/graphql

# Panther REST API URL
# Only change this if you're using a custom Panther instance
PANTHER_REST_API_URL=https://api.runpanther.com
```

Replace `your_panther_api_key_here` with your actual Panther API key, and optionally update the API URLs if you're using a custom Panther instance.

## Project Structure

```
.
├── src/
│   └── mcp_panther/
│       ├── __init__.py
│       └── server.py
├── .env.example
├── pyproject.toml
├── requirements.txt
└── LICENSE
```

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

This starts the MCP server and provides an interactive web interface to test its functionality.

### Option 3: Run as a Standalone Server

You can also run the server directly:

```bash
uv run python -m mcp_panther.server
```

This will start the server at http://127.0.0.1:8000/

```

## Available Tools

The server provides the following tools:

1. `list_alerts`: List alerts from Panther with optional date range, severity, and status filters
2. `get_alert_by_id`: Get detailed information about a specific alert
3. `list_sources`: List log sources with optional filters
4. `execute_data_lake_query`: Execute SQL queries against Panther's data lake
5. `get_data_lake_query_results`: Get results from a previously executed data lake query
6. `list_rules`: List all Panther rules with optional pagination
7. `get_rule_by_id`: Get detailed information about a specific rule

## Available Resources

The server provides the following resources:

1. `config://panther`: Provides configuration information about the Panther API.

## Available Prompts

The server provides the following prompts:

1. `triage_alert`: Helps triage a specific alert by analyzing its details and associated events
2. `prioritize_alerts`: Helps prioritize alerts based on severity, impact, and related events

## Troubleshooting

- If you encounter authentication errors, make sure your Panther API key is correct and has the necessary permissions.
- Check the server logs for detailed error messages.
- Ensure your Panther API URLs are correctly set if you're using a custom Panther instance.
- If you see an error like `typer is required`, make sure you've installed MCP with CLI components: `pip install mcp[cli]`
- Ensure you have `npm` and `uv` installed globally on your system.

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.
