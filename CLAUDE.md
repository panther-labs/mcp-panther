# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Development Commands

**Setup and Dependencies:**
```bash
make venv          # Create virtual environment
make dev-deps      # Install dev dependencies  
make sync          # Sync dependencies
```

**Code Quality:**
```bash
make fmt           # Format code with ruff
make lint          # Lint code with ruff
make test          # Run pytest with coverage
make integration-test  # Run integration tests (requires FASTMCP_INTEGRATION_TEST=1)
```

**Development Server:**
```bash
make mcp-dev       # Run FastMCP dev server
uv run python -m mcp_panther.server  # Run server directly
uvx mcp-panther    # Run as installed package
```

**Single Test Execution:**
```bash
uv run pytest tests/path/to/test_file.py::test_function_name
```

## Architecture Overview

**Core Framework:** FastMCP-based MCP server providing security platform integration

**Key Components:**
- **Server Entry Point** (`server.py`): FastMCP server with dual transport support (stdio/streamable-http)
- **Registry System**: Decorator-based auto-registration for tools, prompts, and resources
- **Client Layer** (`client.py`): Dual GraphQL/REST client with async session management
- **Permission System** (`permissions.py`): Fine-grained access control mapped to Panther permissions

**Tool Architecture:**
- Tools organized by domain: alerts, data_lake, metrics, rules, schemas, sources, users
- Each tool decorated with `@mcp_tool` for auto-registration
- Permission annotations using `all_perms()` or `any_perms()` decorators
- Consistent async patterns with proper error handling

**Registry Pattern:**
```python
@mcp_tool
@all_perms(PantherPermissions.DATA_READ)
async def tool_name(param: str) -> dict:
    # Tool implementation
```

## Environment Configuration

**Required Variables:**
- `PANTHER_INSTANCE_URL`: Panther instance URL (e.g., https://your-instance.domain)
- `PANTHER_API_TOKEN`: API token with appropriate permissions

**Transport Configuration:**
- `MCP_TRANSPORT`: stdio (default) or streamable-http
- `MCP_PORT`: HTTP transport port (default: 3000)
- `MCP_HOST`: HTTP transport host (default: 127.0.0.1)

**Logging:**
- `LOG_LEVEL`: Logging level (default: WARNING)
- `MCP_LOG_FILE`: Optional log file path

## Testing Patterns

**Test Structure:**
- Unit tests mirror source structure in `tests/panther_mcp_core/`
- Integration tests require `FASTMCP_INTEGRATION_TEST=1` environment variable
- Mock utilities available in `tests/utils/helpers.py`

**Key Testing Notes:**
- Always run linting after code changes: `make lint`
- Integration tests start real servers - ensure proper cleanup
- Use async test patterns with pytest-asyncio

## Client Architecture Patterns

**Dual Client Support:**
- GraphQL client for complex queries (alerts, rules)
- REST client for simpler operations (metrics, schemas)
- Automatic session management with async context managers
- Built-in retry logic and error handling

**Error Handling:**
- 401/403 errors provide user-friendly permission messages
- SSL verification enabled by default
- User-agent tracking for audit trails

## Permission Model

**Permission Mapping:**
- Enum-based permissions (`PantherPermissions`) map to Panther's permission strings
- Tools require either "all of" or "any of" specified permissions
- Permission validation happens at tool invocation time

## Code Quality Standards

**Ruff Configuration:**
- Enabled rules: pycodestyle (E), pyflakes (F), isort (I), pep8-naming (N), type-checking (TCH)
- Max complexity: 10
- Import sorting: mcp_panther as first-party package
- Python 3.12+ type hints required