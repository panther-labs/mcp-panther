# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the Panther MCP (Model Context Protocol) Server, a Python-based server that provides AI assistant functionality for Panther security platform users. The project enables AI assistants to write/tune detections, query security logs, and manage alerts through Panther's APIs.

## Development Commands

### Core Commands
- `make test` - Run all tests using pytest
- `make lint` - Run ruff linting checks
- `make fmt` - Format code using ruff
- `uv sync` - Install dependencies from pyproject.toml
- `uv sync --group dev` - Install development dependencies

### Development Server
- `make mcp-dev` - Start development server using fastmcp
- `make integration-test` - Run integration tests against live Panther instance

### Environment Setup
- `make venv` - Create virtual environment using uv
- `make dev-deps` - Install dev dependencies (run after activating venv)

## Architecture

### Registry Pattern
The codebase uses a decorator-based registry pattern for automatic component discovery:

- **Tools**: Decorated with `@mcp_tool`, collected in `tools/registry.py`
- **Prompts**: Decorated with `@mcp_prompt`, collected in `prompts/registry.py` 
- **Resources**: Decorated with `@mcp_resource`, collected in `resources/registry.py`

### Tool Organization
Tools are organized by functional domain in `src/mcp_panther/panther_mcp_core/tools/`:
- `alerts.py` - Alert management operations
- `rules.py` - Detection rule CRUD operations
- `data_lake.py` - SQL queries against data lake
- `sources.py` - Log source management
- `metrics.py` - Alert and rule metrics
- `users.py` - User management
- `schemas.py` - Schema operations

### Client Architecture
Two client types for Panther API interaction:
- **GraphQL Client**: Complex queries using `gql` library (`client.py`)
- **REST Client**: CRUD operations using `aiohttp` (`client.py`)

### Permission System
Tools can specify required permissions via annotations:
```python
@mcp_tool(annotations={"permissions": all_perms(Permission.ALERT_READ)})
```

## Configuration

### Environment Variables
- `PANTHER_INSTANCE_URL` - Panther instance URL (required)
- `PANTHER_API_TOKEN` - API authentication token (required)
- `LOG_LEVEL` - Logging level (default: WARNING)

### Development vs Production
- Development: Uses `fastmcp dev` for hot reloading
- Production: Uses stdio or SSE transport modes

## Testing

### Test Structure
- Unit tests in `tests/` mirror source structure
- Integration tests require live Panther instance
- Coverage reports generated with pytest-cov

### Running Tests
- All tests: `make test` or `uv run pytest`
- Specific test: `uv run pytest tests/path/to/test.py`
- Integration only: `make integration-test`

## Code Style

### Linting and Formatting
- Uses ruff for both linting and formatting
- Configuration in `pyproject.toml`
- Run `make fmt` before committing changes
- Run `make lint` to check for issues

### Import Organization
- First-party imports: `mcp_panther`
- Known first-party configured in ruff settings

## Cursor Rules Integration

When implementing API functionality:
1. GraphQL endpoints must comply with `panther.graphql` schema
2. REST endpoints must comply with `panther_open_api_v3_spec.yaml`
3. Update README.md after adding new user-facing functionality

## Adding New Tools

1. Create tool function in appropriate module under `tools/`
2. Decorate with `@mcp_tool` and specify permissions
3. Import in `tools/__init__.py` to trigger registration
4. Add unit tests following existing patterns
5. Update README.md if user-facing

## Common Development Tasks

When making API calls, always use the existing client infrastructure:
- GraphQL: Use `_execute_query()` function 
- REST: Use `PantherRestClient` context manager

When adding permissions, define new enum values in `permissions.py` and reference in tool annotations.

Follow the existing error handling patterns for API failures and permission denials.

## Data Lake Query Features

### Snowflake Reserved Words Handling
The data lake query execution automatically handles Snowflake reserved words according to their official usage constraints:

#### Automatic Column Quoting
- **ANSI Reserved Words**: Automatically quotes reserved words like `column`, `order`, `table` when used as column names
- **Snowflake Reserved Words**: Quotes Snowflake-specific reserved words like `action`, `regexp`, `qualify`, `ilike`
- **Smart Context Detection**: Only quotes words when they appear as column names in SELECT clauses
- **Function Preservation**: Functions like `CURRENT_TIMESTAMP()` are left unchanged

#### Forbidden Usage Detection
Returns validation errors for words that cannot be used in certain contexts:
- **Scalar Expression Forbidden**: `false`, `true`, `case`, `when`, `cast` cannot be used as column references
- **Column Name Forbidden**: `current_date`, `current_time`, etc. cannot be used as column names
- **FROM Clause Forbidden**: `join`, `left`, `right`, etc. cannot be used as table names or aliases

#### Examples

**Valid Usage (Automatic Quoting):**
```sql
-- Input
SELECT action, column, regexp FROM aws_vpcflow WHERE p_event_time >= '2024-01-01'

-- Automatically becomes
SELECT "action", "column", "regexp" FROM aws_vpcflow WHERE p_event_time >= '2024-01-01'
```

**Invalid Usage (Returns Error):**
```sql
-- This will be rejected
SELECT false, true FROM logs WHERE p_event_time >= '2024-01-01'
-- Error: 'FALSE' cannot be used as column reference in scalar expressions
```

The implementation follows the official Snowflake reserved words documentation and provides clear error messages for forbidden usage patterns.