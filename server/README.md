# MCP Panther Developer Guide

This guide provides instructions for developers working on the MCP Panther project, covering how to test changes and how to extend the functionality by adding new tools, prompts, and resources.

## Table of Contents

- [Getting Started](#getting-started)
- [Testing Changes](#testing-changes)
  - [Manual Testing](#manual-testing)
  - [Debugging](#debugging)
- [Extending Functionality](#extending-functionality)
  - [Adding New Tools (`mcp_tool`)](#adding-new-tools-mcp_tool)
  - [Adding New Prompts (`mcp_prompt`)](#adding-new-prompts-mcp_prompt)
  - [Adding New Resources (`mcp_resource`)](#adding-new-resources-mcp_resource)
- [Code Quality](#code-quality)
  - [Linting with Ruff](#linting-with-ruff)
- [Best Practices](#best-practices)
- [Common Issues](#common-issues)

## Getting Started

The MCP Panther project is a server implementation for the Model Control Protocol (MCP) that provides integration with Panther Labs services.

## Testing Changes

### Manual Testing

To manually test your changes, you can run the MCP server using:

```bash
uv run fastmcp dev src/mcp_panther/server.py
```

This command runs the server in development mode, which provides additional debugging information and automatically reloads when changes are detected.

Or add the following to your MCP client configuration:

```json
{
  "mcpServers": {
    "panther": {
      "command": "uv",
      "args": [
        "run",
        "--with",
        "fastmcp",
        "--with",
        "anyascii",
        "--with",
        "aiohttp",
        "--with",
        "gql[aiohttp]",
        "fastmcp",
        "run",
        "/<PATH-TO-MCP-PANTHER-REPO>/src/mcp_panther/server.py"
      ],
      "env": {
        "PANTHER_API_TOKEN": "<TOKEN-HERE>",
        "PANTHER_INSTANCE_URL": "https://<INSTANCE-URL-HERE>"
      }
    }
  }
}
```

### Debugging

When running the server, you can set the logging level to DEBUG in `server.py` for more detailed logs:

```python
logging.basicConfig(
    level=logging.DEBUG,  # Set to INFO for less verbose output
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
```
To send logs to a file instead, run the server with `--log-file <path>` or set the
`MCP_LOG_FILE` environment variable. Logs from FastMCP will also be written to the
configured file.

### Run the Development Server

For testing and development, you can run the MCP server in development mode:

```bash
uv run fastmcp dev src/mcp_panther/server.py
```

This starts the MCP Inspector server and provides an interactive web interface to test its functionality.

### Run as a Standalone Server

You can also run the server directly:

```bash
uv run python -m mcp_panther.server
```

This will start the server at http://127.0.0.1:8000/

## Extending Functionality

The MCP Panther server functionality can be extended by adding tools, prompts, and resources.

### Adding New Tools (`mcp_tool`)

Tools are functions that perform specific actions with Panther and are exposed to MCP clients.

1. Create a new Python file in `src/mcp_panther/panther_mcp_core/tools/` or add to an existing one
2. Import the `mcp_tool` decorator from the registry:

```python
from .registry import mcp_tool
```

3. Define your function and annotate it with the `mcp_tool` decorator:

```python
@mcp_tool
async def my_new_tool(param1: str, param2: int = 0) -> dict:
    """
    Description of what this tool does.
    
    Args:
        param1: Description of parameter 1
        param2: Description of parameter 2
        
    Returns:
        A dictionary with the results
    """
    # Tool implementation
    result = {"status": "success", "data": [...]}
    return result
```

4. Make sure your tool is imported in `__init__.py` if you created a new file:

```python
# In src/mcp_panther/panther_mcp_core/tools/__init__.py
from . import my_new_module  # Add this line
```

5. Update the `__all__` list if you created a new module:

```python
__all__ = ["alerts", "rules", "data_lake", "sources", "metrics", "users", "my_new_module"]
```

### Adding New Prompts (`mcp_prompt`)

Prompts are functions that generate prompt templates for LLMs.

1. Create a new Python file in `src/mcp_panther/panther_mcp_core/prompts/` or add to an existing one
2. Import the `mcp_prompt` decorator from the registry:

```python
from .registry import mcp_prompt
```

3. Define your function and annotate it with the `mcp_prompt` decorator:

```python
@mcp_prompt
def my_new_prompt(context_info: str) -> str:
    """
    Generate a prompt for a specific task.
    
    Args:
        context_info: Contextual information to include in the prompt
        
    Returns:
        A string containing the prompt template
    """
    return f"""
    You are a security analyst. Here is some context information:
    {context_info}
    
    Based on this information, please analyze the security implications.
    """
```

4. Make sure your prompt is imported in `__init__.py` if you created a new file:

```python
# In src/mcp_panther/panther_mcp_core/prompts/__init__.py
from . import my_new_module  # Add this line
```

5. Update the `__all__` list if you created a new module:

```python
__all__ = ["alert_triage", "my_new_module"]
```

### Adding New Resources (`mcp_resource`)

Resources are functions that provide configuration or data to MCP clients.

1. Create a new Python file in `src/mcp_panther/panther_mcp_core/resources/` or add to an existing one
2. Import the `mcp_resource` decorator from the registry:

```python
from .registry import mcp_resource
```

3. Define your function and annotate it with the `mcp_resource` decorator, specifying the resource path:

```python
@mcp_resource("config://panther/my-resource")
def my_new_resource() -> dict:
    """
    Provide a new resource.
    
    Returns:
        A dictionary with the resource data
    """
    return {
        "key1": "value1",
        "key2": "value2",
        # More resource data...
    }
```

4. Make sure your resource is imported in `__init__.py` if you created a new file:

```python
# In src/mcp_panther/panther_mcp_core/resources/__init__.py
from . import my_new_module  # Add this line
```

5. Update the `__all__` list if you created a new module:

```python
__all__ = ["config", "my_new_module"]
```

## Code Quality

### Linting with Ruff

The project uses Ruff for linting. You can run linting checks with:

```bash
ruff check .
```

To automatically fix issues:

```bash
ruff check --fix .
```

To format the code:

```bash
ruff format .
```

## Best Practices

### Code Quality
1. **Type Safety**: Include type annotations for parameters and return values
2. **Documentation**: Write clear docstrings and maintain consistent terminology (e.g., use "log type schemas" instead of mixing "schemas" and "log types")
3. **Error Handling**: Implement robust error handling, especially for external service interactions
4. **Performance**: Use async functions for I/O operations and limit response lengths to prevent context window flooding

### Development Process
1. **Testing**: Test changes thoroughly before submitting PRs
2. **Logging**: Use appropriate log levels for debugging and monitoring
3. **Tool Design**: Write clear, focused tool descriptions to help LLMs make appropriate choices

## Common Issues

- **Import Errors**: Make sure new modules are properly imported in `__init__.py` files.
- **MCP Registration**: All tools, prompts, and resources must be decorated with the appropriate decorator to be registered with MCP.
- **Unused Imports**: Use `__all__` lists to avoid unused import warnings. 
