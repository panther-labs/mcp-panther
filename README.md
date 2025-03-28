# Panther MCP Server

This is a Model Context Protocol (MCP) server for Panther that provides functionality to:
1. Authenticate with Panther using a Panther API key
2. Connect to Panther via GraphQL and list alerts from today

## Prerequisites

- Python 3.8 or higher
- Panther API key
- MCP client (like Claude Desktop App) to interact with the server

## Installation

1. Clone this repository or download the files.

2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

This will install MCP with CLI components, which are necessary for the `mcp install` and `mcp dev` commands.

3. Create a `.env` file in the same directory with your Panther API key:

```
PANTHER_API_KEY=your_panther_api_key_here
PANTHER_API_URL=https://api.your-panther-instance.com/public/graphql
```

Replace `your_panther_api_key_here` with your actual Panther API key, and optionally update the API URL if you're using a custom Panther instance.

## File Structure

- `mcp_panther_module.py` - The core MCP server module with tools and resources
- `run_panther_mcp.py` - Runner script to start the server
- `.env.example` - Example environment variable configuration
- `requirements.txt` - Python dependencies

## Usage

### Option 1: Install in Claude Desktop App

The simplest way to use this server is to install it in the Claude Desktop App:

```bash
mcp install mcp_panther_module.py
```

This will make the Panther MCP server available to Claude directly.

### Option 2: Run the Development Server

For testing and development, you can run the MCP server in development mode:

```bash
mcp dev mcp_panther_module.py
```

This starts the MCP server and provides an interactive web interface to test its functionality.

### Option 3: Run as a Standalone Server

You can also run the server directly:

```bash
python run_panther_mcp.py
```

This will start the server at http://127.0.0.1:8000/

If you're using a virtual environment tool like pipenv or uv, make sure to run the command within the appropriate environment:

```bash
# Using pipenv
pipenv run python run_panther_mcp.py

# Using uv
uv run python run_panther_mcp.py
```

## Available Tools

The server provides the following tools:

1. `authenticate_with_panther`: Tests authentication with Panther using the API key.
2. `get_todays_alerts`: Retrieves alerts from Panther for the current day.

## Available Resources

The server provides the following resources:

1. `config://panther`: Provides configuration information about the Panther API.

## Troubleshooting

- If you encounter authentication errors, make sure your Panther API key is correct and has the necessary permissions.
- Check the server logs for detailed error messages.
- Ensure your Panther API URL is correctly set if you're using a custom Panther instance.
- If you see an error like `typer is required`, make sure you've installed MCP with CLI components: `pip install mcp[cli]`

## License

This project is licensed under the MIT License - see the LICENSE file for details.
