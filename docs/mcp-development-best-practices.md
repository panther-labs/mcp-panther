# MCP Development Best Practices

This document outlines best practices for developing Model Context Protocol (MCP) servers using FastMCP, based on the official FastMCP documentation and our experience building the Panther MCP server.

## Table of Contents

- [Core Principles](#core-principles)
- [Tool Design](#tool-design)
- [Parameter Patterns](#parameter-patterns)
- [Error Handling](#error-handling)
- [Performance Considerations](#performance-considerations)
- [Security Best Practices](#security-best-practices)
- [Documentation Standards](#documentation-standards)

## Core Principles

### 1. Use Type Annotations Consistently

Always provide comprehensive type annotations for all function parameters and return values:

```python
@mcp.tool
async def get_alert(alert_id: str, ctx: Context) -> dict[str, Any]:
    """Get detailed information about a specific alert."""
    # Implementation
```

### 2. Leverage Pydantic Field Annotations

Use the `Annotated[Type, Field()]` pattern for all parameters to provide rich metadata:

```python
from typing import Annotated
from pydantic import Field

@mcp.tool
async def list_alerts(
    start_date: Annotated[
        str | None,
        Field(
            description="Start date in ISO 8601 format (e.g. '2024-03-20T00:00:00Z')",
            examples=["2024-03-20T00:00:00Z"]
        ),
    ] = None,
    severities: Annotated[
        list[str],
        Field(
            description="List of severities to filter by",
            examples=[["CRITICAL", "HIGH", "MEDIUM"]]
        ),
    ] = ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
) -> dict[str, Any]:
    """List alerts with comprehensive filtering options."""
    # Implementation
```

### 3. Method Registration Patterns

**Avoid** directly decorating instance/class methods. Instead, register methods after instantiation:

```python
# ❌ Don't do this
class AlertManager:
    @mcp.tool  # Avoid direct decoration
    def get_alert(self, alert_id: str):
        pass

# ✅ Do this instead
class AlertManager:
    def get_alert(self, alert_id: str):
        pass

alert_manager = AlertManager()
mcp.tool(alert_manager.get_alert)  # Register after instantiation
```

### 4. Use Context for Advanced Capabilities

Leverage the MCP Context for logging, progress reporting, and state management:

```python
@mcp.tool
async def process_large_dataset(
    dataset_id: str, 
    ctx: Context
) -> dict[str, Any]:
    await ctx.info("Starting dataset processing")
    
    # Use progress reporting for long operations
    for i in range(100):
        await ctx.report_progress(i, 100, f"Processing item {i}")
        # Process item
    
    await ctx.info("Dataset processing completed")
    return {"status": "success", "processed_count": 100}
```

## Tool Design

### 1. Single Responsibility Principle

Each tool should have a single, well-defined purpose:

```python
# ✅ Good: Single responsibility
@mcp.tool
async def get_alert(alert_id: str) -> dict[str, Any]:
    """Get detailed information about a specific alert."""

@mcp.tool
async def update_alert_status(alert_id: str, status: str) -> dict[str, Any]:
    """Update the status of a specific alert."""

# ❌ Avoid: Multiple responsibilities
@mcp.tool
async def manage_alert(alert_id: str, action: str, **kwargs) -> dict[str, Any]:
    """Perform various alert management actions."""  # Too generic
```

### 2. Clear, Descriptive Names

Tool names should be intuitive and descriptive. Remove redundant suffixes:

```python
# ✅ Good: Clean, descriptive names
get_alert()
list_alerts()
update_alert_status()

# ❌ Avoid: Redundant suffixes
get_alert_by_id()  # "_by_id" is implied
list_all_alerts()  # "all" is implied by "list"
```

### 3. Consistent Return Patterns

Establish consistent patterns for return values across all tools:

```python
# Success response pattern
return {
    "success": True,
    "data": result_data,
    "message": "Operation completed successfully"
}

# Error response pattern
return {
    "success": False,
    "error": error_message,
    "details": error_details
}
```

## Parameter Patterns

### 1. Core Annotated Field Pattern Structure

When defining tool parameters, always use the `Annotated` pattern with `Field()` objects:

```python
param_name: Annotated[
    Type | None,  # or just Type for required params
    Field(
        description="Clear description of the parameter",
        examples=["example1", "example2"],  # when helpful
    ),
] = default_value
```

### 2. Parameter Type Patterns

#### Required Parameters (No Default)

```python
user_id: Annotated[
    str,
    Field(
        description="The ID of the user to fetch",
        examples=["user-123"],
    ),
]
```

#### Optional String Parameters

```python
cursor: Annotated[
    str | None,
    Field(description="Optional cursor for pagination from a previous query"),
] = None
```

#### String Parameters with Specific Defaults

```python
sort_dir: Annotated[
    str | None,
    Field(
        description="The sort direction for the results",
        examples=["asc", "desc"]
    ),
] = "asc"
```

#### Boolean Parameters with Meaningful Defaults

```python
is_healthy: Annotated[
    bool,
    Field(description="Filter by health status (default: True)"),
] = True
```

Prefer concrete defaults over None when the meaning is clear:

```python
is_archived: Annotated[
    bool,
    Field(description="Filter by archive status (default: False shows non-archived)"),
] = False
```

#### List Parameters with Empty Defaults

```python
log_types: Annotated[
    list[str],
    Field(
        description="Optional list of log types to filter by",
        examples=[["AWS.CloudTrail", "AWS.S3ServerAccess"]],
    ),
] = []
```

#### Integer Parameters with Constraints

```python
page_size: Annotated[
    int,
    Field(
        description="Number of results per page",
        examples=[25, 50, 100],
        ge=1,      # Greater than or equal to 1
        le=1000,   # Less than or equal to 1000
    ),
] = 25
```

### 3. Annotated Field Guidelines

1. **Always use `Field()` with descriptive text** - never rely on parameter names alone
2. **Include `examples=[]` for complex parameters** - especially lists, enums, and structured data
3. **Use meaningful defaults instead of None when possible:**
   - `[]` for lists that should be empty by default
   - `False/True` for boolean filters with clear default behavior
   - Specific string values when there's a sensible default
4. **Consistent type patterns:** `str | None`, `list[str]`, `dict[str, Any]`
5. **Never use `Literals` or `Enums`** - they have mixed results with AI tools
6. **Description should explain the parameter's purpose and default behavior**

### 4. Validation and Constraints

Use Pydantic constraints for parameter validation:

```python
from pydantic import Field

@mcp.tool
async def list_alerts(
    page_size: Annotated[
        int,
        Field(
            description="Number of results per page",
            ge=1,      # Greater than or equal to 1
            le=1000,   # Less than or equal to 1000
        ),
    ] = 25,
    timeout: Annotated[
        int,
        Field(
            description="Query timeout in seconds",
            ge=1,
            le=300,
        ),
    ] = 30,
) -> dict[str, Any]:
    # Implementation
```

### 5. Enum Handling

Avoid Python enums in favor of simple string/int types with examples:

```python
# ✅ Good: Use examples instead of enums
status: Annotated[
    str,
    Field(
        description="The status to set for the alert",
        examples=["OPEN", "TRIAGED", "RESOLVED", "CLOSED"],
    ),
]

# ❌ Avoid: Python enums can cause issues with AI tools
from enum import Enum
class AlertStatus(Enum):
    OPEN = "OPEN"
    TRIAGED = "TRIAGED"
```

## Error Handling

### 1. Comprehensive Error Responses

Provide detailed error information without exposing sensitive data:

```python
@mcp.tool
async def get_alert(alert_id: str) -> dict[str, Any]:
    try:
        result = await fetch_alert(alert_id)
        return {
            "success": True,
            "alert": result,
        }
    except AlertNotFoundError:
        return {
            "success": False,
            "error": f"Alert with ID '{alert_id}' not found",
            "error_code": "ALERT_NOT_FOUND",
        }
    except PermissionError:
        return {
            "success": False,
            "error": "Insufficient permissions to access this alert",
            "error_code": "PERMISSION_DENIED",
        }
    except Exception as e:
        return {
            "success": False,
            "error": "An unexpected error occurred",
            "error_code": "INTERNAL_ERROR",
            # Don't expose internal error details in production
        }
```

### 2. Input Validation

Validate inputs early and provide clear error messages:

```python
@mcp.tool
async def update_alert_status(
    alert_id: str,
    status: str,
) -> dict[str, Any]:
    # Validate inputs
    if not alert_id or not alert_id.strip():
        return {
            "success": False,
            "error": "Alert ID cannot be empty",
            "error_code": "INVALID_INPUT",
        }
    
    valid_statuses = {"OPEN", "TRIAGED", "RESOLVED", "CLOSED"}
    if status not in valid_statuses:
        return {
            "success": False,
            "error": f"Invalid status '{status}'. Must be one of: {', '.join(valid_statuses)}",
            "error_code": "INVALID_STATUS",
        }
    
    # Proceed with implementation
```

## Performance Considerations

### 1. Async/Await for I/O Operations

Always use async functions for I/O-bound operations:

```python
@mcp.tool
async def query_data_lake(sql: str) -> dict[str, Any]:
    """Execute SQL query against data lake."""
    async with get_database_connection() as conn:
        result = await conn.execute(sql)
        return {"success": True, "results": result}
```

### 2. Pagination for Large Datasets

Implement pagination for operations that could return large datasets:

```python
@mcp.tool
async def list_alerts(
    cursor: Annotated[
        str | None,
        Field(description="Pagination cursor from previous query"),
    ] = None,
    page_size: Annotated[
        int,
        Field(description="Number of results per page"),
    ] = 25,
) -> dict[str, Any]:
    # Implementation with pagination
    return {
        "success": True,
        "alerts": results,
        "has_next_page": has_more,
        "next_cursor": next_cursor,
    }
```

### 3. Response Size Limits

Limit response sizes to prevent context window overflow:

```python
@mcp.tool
async def get_alert_events(
    alert_id: str,
    limit: Annotated[
        int,
        Field(description="Maximum number of events to return"),
    ] = 10,  # Default to small number
) -> dict[str, Any]:
    # Ensure limit doesn't exceed maximum
    limit = min(limit, 100)  # Hard cap at 100
    # Implementation
```

## Security Best Practices

### 1. Input Sanitization

Sanitize all inputs, especially for SQL queries and external API calls:

```python
import sqlparse

@mcp.tool
async def query_data_lake(sql: str) -> dict[str, Any]:
    # Parse and validate SQL
    try:
        parsed = sqlparse.parse(sql)
        if not parsed:
            return {"success": False, "error": "Invalid SQL query"}
    except Exception:
        return {"success": False, "error": "Failed to parse SQL query"}
    
    # Additional validation logic
    # Execute query
```

### 2. Permission Checks

Implement proper authorization checks:

```python
@mcp.tool
async def disable_detection(
    detection_id: str,
    ctx: Context,
) -> dict[str, Any]:
    # Check permissions first
    permissions = await get_user_permissions(ctx)
    if "Manage Rules" not in permissions and "Manage Policies" not in permissions:
        return {
            "success": False,
            "error": "Insufficient permissions. Requires 'Manage Rules' or 'Manage Policies'",
            "error_code": "PERMISSION_DENIED",
        }
    
    # Proceed with operation
```

### 3. Sensitive Data Handling

Never log or return sensitive information:

```python
@mcp.tool
async def authenticate_user(username: str, password: str) -> dict[str, Any]:
    # ❌ Never log sensitive data
    # logger.debug(f"Authenticating user {username} with password {password}")
    
    # ✅ Log safely
    logger.debug(f"Authenticating user {username}")
    
    # Don't return sensitive information
    if is_valid_credentials(username, password):
        return {
            "success": True,
            "user_id": get_user_id(username),
            # Don't return password or tokens
        }
```

## Documentation Standards

### 1. Comprehensive Docstrings

Provide clear, comprehensive docstrings for all tools:

```python
@mcp.tool
async def get_alert_event_stats(
    alert_ids: list[str],
    time_window: int = 30,
) -> dict[str, Any]:
    """
    Analyze patterns and relationships across multiple alerts by aggregating their event data.

    For each time window (configurable from 1-60 minutes), the tool collects unique entities
    (IPs, emails, usernames, trace IDs) and alert metadata (IDs, rules, severities) to help
    identify related activities.

    Results are ordered chronologically with the most recent first, helping analysts identify
    temporal patterns, common entities, and potential incident scope.

    Args:
        alert_ids: List of alert IDs to analyze
        time_window: Time window in minutes to group events by (1-60)

    Returns:
        Dict containing analysis results with temporal patterns and common entities
    """
```

### 2. README Tool Tables

Keep README.md tool tables up to date with clear descriptions and sample prompts:

```markdown
| Tool Name | Description | Sample Prompt |
|-----------|-------------|---------------|
| `get_alert` | Get detailed information about a specific alert | "What's the status of alert 8def456?" |
| `list_alerts` | List alerts with comprehensive filtering options | "Show me all high severity alerts from the last 24 hours" |
```

### 3. Code Comments

Add comments for complex business logic but avoid obvious comments:

```python
# ✅ Good: Explains complex business logic
# Panther uses millisecond timestamps, but ISO format expects seconds
timestamp_seconds = timestamp_ms / 1000

# ❌ Avoid: Obvious comments
alert_id = alert["id"]  # Get the alert ID
```

## Testing Integration

Refer to our [MCP Testing Guide](./mcp-testing-guide.md) for comprehensive testing strategies and patterns.

## Additional Resources

- [FastMCP Documentation](https://gofastmcp.com/)
- [MCP Protocol Specification](https://spec.modelcontextprotocol.io/)
- [Tool Design Patterns](./tool-design-patterns.md)
- [Server Architecture Guide](./server-architecture-guide.md)