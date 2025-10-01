# Tool Design Patterns for MCP Servers

This document outlines proven design patterns for creating effective and user-friendly MCP tools, based on FastMCP best practices and real-world experience from the Panther MCP server.

## Table of Contents

- [Fundamental Patterns](#fundamental-patterns)
- [Parameter Design Patterns](#parameter-design-patterns)
- [Response Patterns](#response-patterns)
- [Error Handling Patterns](#error-handling-patterns)
- [Security Patterns](#security-patterns)
- [Performance Patterns](#performance-patterns)
- [Integration Patterns](#integration-patterns)
- [Documentation Patterns](#documentation-patterns)

## Fundamental Patterns

### 1. Single-Purpose Tools

Each tool should have one clear, well-defined purpose:

```python
# ✅ Good: Single purpose tools
@mcp.tool
async def get_alert(alert_id: str) -> dict[str, Any]:
    """Get detailed information about a specific alert."""

@mcp.tool  
async def update_alert_status(alert_ids: list[str], status: str) -> dict[str, Any]:
    """Update the status of one or more alerts."""

# ❌ Avoid: Multi-purpose tools
@mcp.tool
async def manage_alert(alert_id: str, action: str, **kwargs) -> dict[str, Any]:
    """Perform various alert management actions."""  # Too broad
```

### 2. Verb-Noun Naming Convention

Use clear, predictable naming patterns:

```python
# Action patterns
get_alert()        # Retrieve single item
list_alerts()      # Retrieve multiple items  
create_alert()     # Create new item
update_alert()     # Modify existing item
delete_alert()     # Remove item
disable_detection() # Change state

# Query patterns  
query_data_lake()     # Execute queries
search_logs()         # Search operations
summarize_events()    # Analysis operations
```

### 3. Resource-Based Organization

Group related tools by the resources they operate on:

```python
# Alert Management
get_alert()
list_alerts()
update_alert_status()
update_alert_assignee()
add_alert_comment()
list_alert_comments()

# Detection Management
get_detection()
list_detections()
disable_detection()

# Data Lake Operations
query_data_lake()
get_table_schema()
list_databases()
```

## Parameter Design Patterns

### 1. The Annotated Field Pattern

Always use comprehensive field annotations:

```python
from typing import Annotated
from pydantic import Field

@mcp.tool
async def list_alerts(
    # Required parameters (no default)
    start_date: Annotated[
        str,
        Field(
            description="Start date in ISO 8601 format (e.g. '2024-03-20T00:00:00Z')",
            examples=["2024-03-20T00:00:00Z", "2024-01-15T10:30:00Z"]
        ),
    ],
    
    # Optional parameters with None default
    end_date: Annotated[
        str | None,
        Field(
            description="End date in ISO 8601 format (e.g. '2024-03-21T00:00:00Z')",
            examples=["2024-03-21T00:00:00Z"]
        ),
    ] = None,
    
    # Optional parameters with meaningful defaults
    severities: Annotated[
        list[str],
        Field(
            description="List of severities to filter by",
            examples=[["CRITICAL", "HIGH"], ["MEDIUM", "LOW", "INFO"]]
        ),
    ] = ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
    
    # Optional parameters with constraints
    page_size: Annotated[
        int,
        Field(
            description="Number of results per page (1-50)",
            ge=1,
            le=50,
            examples=[25, 10, 50]
        ),
    ] = 25,
) -> dict[str, Any]:
    """List alerts with comprehensive filtering options."""
```

### 2. The Pagination Pattern

Implement consistent pagination across list operations:

```python
@mcp.tool
async def list_alerts(
    cursor: Annotated[
        str | None,
        Field(description="Pagination cursor from previous query"),
    ] = None,
    page_size: Annotated[
        int,
        Field(description="Number of results per page", ge=1, le=100),
    ] = 25,
) -> dict[str, Any]:
    """List alerts with pagination support."""
    
    # Implementation returns:
    return {
        "success": True,
        "alerts": results,
        "has_next_page": bool(next_cursor),
        "next_cursor": next_cursor,
        "total_count": total_count,
    }
```

### 3. The Filter Pattern

Provide comprehensive filtering options:

```python
@mcp.tool
async def list_detections(
    # Text search
    name_contains: Annotated[
        str | None,
        Field(description="Substring search by name (case-insensitive)"),
    ] = None,
    
    # Category filters
    detection_types: Annotated[
        list[str],
        Field(
            description="Detection types to include",
            examples=[["rules"], ["policies"], ["rules", "policies"]]
        ),
    ] = ["rules"],
    
    # State filters
    state: Annotated[
        str,
        Field(
            description="Filter by state",
            examples=["enabled", "disabled"]
        ),
    ] = "enabled",
    
    # Multi-value filters
    severities: Annotated[
        list[str],
        Field(
            description="Filter by severity levels",
            examples=[["HIGH", "CRITICAL"], ["INFO", "LOW"]]
        ),
    ] = ["MEDIUM", "HIGH", "CRITICAL"],
    
    # Tag filters
    tags: Annotated[
        list[str],
        Field(
            description="Filter by tags (case-insensitive)",
            examples=[["AWS", "S3"], ["Initial Access"]]
        ),
    ] = [],
) -> dict[str, Any]:
    """List detections with comprehensive filtering."""
```

### 4. The Validation Pattern

Validate inputs early with clear error messages:

```python
@mcp.tool
async def update_alert_status(
    alert_ids: Annotated[
        list[str],
        Field(description="List of alert IDs to update"),
    ],
    status: Annotated[
        str,
        Field(
            description="New status for the alerts",
            examples=["OPEN", "TRIAGED", "RESOLVED", "CLOSED"]
        ),
    ],
) -> dict[str, Any]:
    """Update the status of one or more alerts."""
    
    # Validate inputs
    if not alert_ids:
        return {
            "success": False,
            "error": "At least one alert ID must be provided",
            "error_code": "MISSING_ALERT_IDS",
        }
    
    valid_statuses = {"OPEN", "TRIAGED", "RESOLVED", "CLOSED"}
    if status not in valid_statuses:
        return {
            "success": False,
            "error": f"Invalid status '{status}'. Must be one of: {', '.join(sorted(valid_statuses))}",
            "error_code": "INVALID_STATUS",
        }
    
    # Validate each alert ID format
    for alert_id in alert_ids:
        if not alert_id or not isinstance(alert_id, str):
            return {
                "success": False,
                "error": f"Invalid alert ID: '{alert_id}'. Must be a non-empty string",
                "error_code": "INVALID_ALERT_ID",
            }
    
    # Proceed with implementation
```

## Response Patterns

### 1. The Success/Error Pattern

Consistent response structure across all tools:

```python
# Success response
{
    "success": True,
    "data": {
        # Tool-specific data
    },
    "message": "Optional success message"
}

# Error response
{
    "success": False,
    "error": "Human-readable error message",
    "error_code": "MACHINE_READABLE_CODE",
    "details": {
        # Optional additional error details
    }
}
```

### 2. The List Response Pattern

Standardized structure for list operations:

```python
@mcp.tool
async def list_alerts(...) -> dict[str, Any]:
    """List alerts with pagination."""
    
    return {
        "success": True,
        "alerts": [...],           # The actual data
        "total_count": 150,        # Total available items
        "page_size": 25,           # Current page size
        "has_next_page": True,     # Whether more pages exist
        "next_cursor": "cursor123", # Pagination cursor
    }
```

### 3. The Detail Response Pattern

Rich detail responses for single-item retrieval:

```python
@mcp.tool
async def get_alert(alert_id: str) -> dict[str, Any]:
    """Get detailed alert information."""
    
    return {
        "success": True,
        "alert": {
            "id": "alert-123",
            "title": "Suspicious Login Activity",
            "severity": "HIGH",
            "status": "OPEN",
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T14:22:00Z",
            "assignee": {
                "id": "user-456",
                "email": "analyst@company.com"
            },
            "rule": {
                "id": "rule-789",
                "name": "Failed Login Detection",
                "severity": "HIGH"
            },
            "event_count": 15,
            "first_event_time": "2024-01-15T10:25:00Z",
            "last_event_time": "2024-01-15T10:35:00Z"
        }
    }
```

### 4. The Bulk Operation Pattern

Consistent handling of bulk operations:

```python
@mcp.tool
async def update_alert_assignee(
    alert_ids: list[str],
    assignee_id: str,
) -> dict[str, Any]:
    """Update assignee for multiple alerts."""
    
    successful_ids = []
    failed_ids = []
    
    for alert_id in alert_ids:
        try:
            await update_single_alert_assignee(alert_id, assignee_id)
            successful_ids.append(alert_id)
        except Exception as e:
            failed_ids.append({
                "alert_id": alert_id,
                "error": str(e)
            })
    
    return {
        "success": True,
        "updated_alerts": successful_ids,
        "failed_alerts": failed_ids,
        "summary": {
            "total_requested": len(alert_ids),
            "successful": len(successful_ids),
            "failed": len(failed_ids)
        }
    }
```

## Error Handling Patterns

### 1. The Layered Error Pattern

Handle errors at multiple levels with appropriate responses:

```python
@mcp.tool
async def get_alert(alert_id: str) -> dict[str, Any]:
    """Get alert with comprehensive error handling."""
    
    try:
        # Input validation layer
        if not alert_id or not alert_id.strip():
            return {
                "success": False,
                "error": "Alert ID cannot be empty",
                "error_code": "INVALID_INPUT"
            }
        
        # Business logic layer
        alert = await fetch_alert_from_api(alert_id)
        
        return {
            "success": True,
            "alert": alert
        }
            
    except AlertNotFoundError:
        return {
            "success": False,
            "error": f"Alert with ID '{alert_id}' not found",
            "error_code": "ALERT_NOT_FOUND"
        }
    except PermissionError:
        return {
            "success": False,
            "error": "Insufficient permissions to access this alert",
            "error_code": "PERMISSION_DENIED"
        }
    except RateLimitError:
        return {
            "success": False,
            "error": "API rate limit exceeded. Please try again later",
            "error_code": "RATE_LIMITED"
        }
    except ConnectionError:
        return {
            "success": False,
            "error": "Unable to connect to Panther API",
            "error_code": "CONNECTION_ERROR"
        }
    except Exception as e:
        # Log the full error for debugging
        logger.exception(f"Unexpected error in get_alert for ID {alert_id}")
        
        return {
            "success": False,
            "error": "An unexpected error occurred",
            "error_code": "INTERNAL_ERROR"
        }
```

### 2. The Graceful Degradation Pattern

Provide partial results when some operations fail:

```python
@mcp.tool
async def get_alert_with_events(alert_id: str) -> dict[str, Any]:
    """Get alert with events, gracefully handling event fetch failures."""
    
    try:
        # Get the basic alert info (required)
        alert = await fetch_alert(alert_id)
        
        # Try to get events (optional)
        events = []
        events_error = None
        
        try:
            events = await fetch_alert_events(alert_id, limit=10)
        except Exception as e:
            events_error = str(e)
            logger.warning(f"Failed to fetch events for alert {alert_id}: {e}")
        
        return {
            "success": True,
            "alert": alert,
            "events": events,
            "events_available": len(events) > 0,
            "events_error": events_error,
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to fetch alert: {str(e)}",
            "error_code": "ALERT_FETCH_ERROR"
        }
```

## Security Patterns

### 1. The Permission Check Pattern

Consistent permission validation:

```python
async def check_permissions(required_permissions: list[str], ctx: Context) -> dict[str, Any] | None:
    """Check if user has required permissions. Returns error dict if not authorized."""
    
    try:
        user_permissions = await get_user_permissions(ctx)
        
        # Check if user has any of the required permissions
        if not any(perm in user_permissions for perm in required_permissions):
            return {
                "success": False,
                "error": f"Insufficient permissions. Requires one of: {', '.join(required_permissions)}",
                "error_code": "PERMISSION_DENIED"
            }
        
        return None  # No error, user is authorized
        
    except Exception as e:
        return {
            "success": False,
            "error": "Failed to verify permissions",
            "error_code": "PERMISSION_CHECK_ERROR"
        }

@mcp.tool
async def disable_detection(
    detection_id: str,
    ctx: Context,
) -> dict[str, Any]:
    """Disable a detection with permission check."""
    
    # Check permissions first
    perm_error = await check_permissions(["Manage Rules", "Manage Policies"], ctx)
    if perm_error:
        return perm_error
    
    # Proceed with operation
    # ...
```

### 2. The Input Sanitization Pattern

Clean and validate all inputs:

```python
import sqlparse
import re

@mcp.tool
async def query_data_lake(sql: str) -> dict[str, Any]:
    """Execute SQL query with comprehensive input validation."""
    
    # Basic validation
    if not sql or not sql.strip():
        return {
            "success": False,
            "error": "SQL query cannot be empty",
            "error_code": "EMPTY_QUERY"
        }
    
    # Length validation
    if len(sql) > 10000:  # 10KB limit
        return {
            "success": False,
            "error": "Query too long. Maximum 10,000 characters allowed",
            "error_code": "QUERY_TOO_LONG"
        }
    
    # SQL parsing validation
    try:
        parsed = sqlparse.parse(sql.strip())
        if not parsed:
            return {
                "success": False,
                "error": "Invalid SQL query",
                "error_code": "INVALID_SQL"
            }
    except Exception:
        return {
            "success": False,
            "error": "Failed to parse SQL query",
            "error_code": "SQL_PARSE_ERROR"
        }
    
    # Check for required p_event_time filter
    sql_lower = sql.lower()
    if 'p_event_time' not in sql_lower:
        return {
            "success": False,
            "error": "Query must include a p_event_time filter for performance",
            "error_code": "MISSING_TIME_FILTER"
        }
    
    # Proceed with execution
    # ...
```

## Performance Patterns

### 1. The Timeout Pattern

Implement timeouts for external operations:

```python
import asyncio

@mcp.tool
async def query_data_lake(
    sql: str,
    timeout: Annotated[
        int,
        Field(
            description="Query timeout in seconds",
            ge=1,
            le=300
        ),
    ] = 30,
) -> dict[str, Any]:
    """Execute SQL query with timeout."""
    
    try:
        # Use asyncio.wait_for for timeout control
        result = await asyncio.wait_for(
            execute_query(sql),
            timeout=timeout
        )
        
        return {
            "success": True,
            "results": result,
            "query_time": result.get("execution_time_ms", 0) / 1000
        }
        
    except asyncio.TimeoutError:
        return {
            "success": False,
            "error": f"Query timed out after {timeout} seconds",
            "error_code": "QUERY_TIMEOUT"
        }
```

### 2. The Batch Processing Pattern

Handle large operations efficiently:

```python
@mcp.tool
async def update_multiple_alerts(
    alert_ids: list[str],
    updates: dict[str, Any],
) -> dict[str, Any]:
    """Update multiple alerts in batches."""
    
    batch_size = 50  # Process in batches of 50
    successful_updates = []
    failed_updates = []
    
    for i in range(0, len(alert_ids), batch_size):
        batch = alert_ids[i:i + batch_size]
        
        try:
            # Process batch
            batch_results = await update_alert_batch(batch, updates)
            successful_updates.extend(batch_results.get("successful", []))
            failed_updates.extend(batch_results.get("failed", []))
            
        except Exception as e:
            # Mark entire batch as failed
            failed_updates.extend([
                {"alert_id": aid, "error": str(e)} 
                for aid in batch
            ])
    
    return {
        "success": True,
        "summary": {
            "total_requested": len(alert_ids),
            "successful": len(successful_updates),
            "failed": len(failed_updates)
        },
        "successful_updates": successful_updates,
        "failed_updates": failed_updates
    }
```

### 3. The Response Size Limiting Pattern

Prevent large responses from overwhelming clients:

```python
@mcp.tool
async def get_alert_events(
    alert_id: str,
    limit: Annotated[
        int,
        Field(
            description="Maximum number of events to return",
            ge=1,
            le=100  # Hard limit to prevent huge responses
        ),
    ] = 10,
) -> dict[str, Any]:
    """Get alert events with size limiting."""
    
    # Enforce absolute maximum
    actual_limit = min(limit, 100)
    
    events = await fetch_alert_events(alert_id, limit=actual_limit)
    
    return {
        "success": True,
        "events": events,
        "event_count": len(events),
        "limit_applied": actual_limit,
        "more_available": len(events) == actual_limit
    }
```

## Integration Patterns

### 1. The GraphQL Client Pattern

Consistent GraphQL interaction:

```python
class PantherGraphQLClient:
    """Centralized GraphQL client for Panther API."""
    
    async def execute_query(
        self,
        query: str,
        variables: dict[str, Any] = None,
        operation_name: str = None
    ) -> dict[str, Any]:
        """Execute GraphQL query with error handling."""
        
        try:
            result = await self.client.execute(
                gql(query),
                variable_values=variables,
                operation_name=operation_name
            )
            return result
            
        except TransportError as e:
            if "403" in str(e):
                raise PermissionError("Insufficient permissions")
            elif "404" in str(e):
                raise NotFoundError("Resource not found")
            else:
                raise ConnectionError(f"API request failed: {e}")

# Usage in tools
@mcp.tool
async def get_alert(alert_id: str) -> dict[str, Any]:
    """Get alert using GraphQL client."""
    
    client = PantherGraphQLClient()
    
    query = """
        query GetAlert($alertId: ID!) {
            alerts(input: {alertIds: [$alertId]}) {
                alertList {
                    id
                    title
                    severity
                    status
                }
            }
        }
    """
    
    try:
        result = await client.execute_query(query, {"alertId": alert_id})
        alerts = result["alerts"]["alertList"]
        
        if not alerts:
            return {
                "success": False,
                "error": f"Alert with ID '{alert_id}' not found",
                "error_code": "ALERT_NOT_FOUND"
            }
        
        return {
            "success": True,
            "alert": alerts[0]
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_code": "API_ERROR"
        }
```

### 2. The Context Usage Pattern

Effective use of MCP Context:

```python
@mcp.tool
async def process_large_operation(
    operation_id: str,
    ctx: Context,
) -> dict[str, Any]:
    """Long-running operation with progress reporting."""
    
    await ctx.info(f"Starting operation {operation_id}")
    
    try:
        # Get total work items
        work_items = await get_work_items(operation_id)
        total_items = len(work_items)
        
        await ctx.info(f"Processing {total_items} items")
        
        processed = 0
        results = []
        
        for i, item in enumerate(work_items):
            # Report progress
            await ctx.report_progress(
                current=i + 1,
                total=total_items,
                description=f"Processing item {item.id}"
            )
            
            # Process item
            result = await process_item(item)
            results.append(result)
            processed += 1
            
            # Log milestone progress
            if processed % 10 == 0:
                await ctx.info(f"Processed {processed}/{total_items} items")
        
        await ctx.info(f"Operation {operation_id} completed successfully")
        
        return {
            "success": True,
            "results": results,
            "processed_count": processed
        }
        
    except Exception as e:
        await ctx.error(f"Operation {operation_id} failed: {str(e)}")
        raise
```

## Documentation Patterns

### 1. The Comprehensive Docstring Pattern

Detailed function documentation:

```python
@mcp.tool
async def get_alert_event_stats(
    alert_ids: list[str],
    start_date: str | None = None,
    end_date: str | None = None,
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
        alert_ids: List of alert IDs to analyze (maximum 50 alerts)
        start_date: Optional start date in ISO 8601 format. Defaults to start of today UTC
        end_date: Optional end date in ISO 8601 format. Defaults to end of today UTC
        time_window: Time window in minutes to group events by (1-60, default: 30)

    Returns:
        Dict containing:
        - success: Boolean indicating if analysis completed
        - results: List of time-grouped analysis results
        - summary: Overview statistics
        - error: Error message if unsuccessful

    Raises:
        ValueError: If alert_ids is empty or time_window is invalid
        PermissionError: If user lacks required permissions

    Example:
        >>> result = await get_alert_event_stats(
        ...     alert_ids=["alert-123", "alert-456"],
        ...     time_window=15
        ... )
        >>> print(f"Found {len(result['results'])} time periods")
    """
```

### 2. The Parameter Documentation Pattern

Clear parameter descriptions with examples:

```python
@mcp.tool
async def list_detections(
    detection_types: Annotated[
        list[str],
        Field(
            description=(
                "One or more detection types to include in results. "
                "Available types: 'rules' (Python rules), 'scheduled_rules' (cron-based rules), "
                "'simple_rules' (YAML rules), 'policies' (cloud resource policies)"
            ),
            examples=[
                ["rules"],  # Python rules only
                ["policies"],  # Cloud policies only  
                ["rules", "simple_rules"],  # Multiple types
            ]
        ),
    ] = ["rules"],
    
    severities: Annotated[
        list[str],
        Field(
            description=(
                "Filter by detection severity levels. Detections with any of the "
                "specified severities will be included in results"
            ),
            examples=[
                ["CRITICAL", "HIGH"],  # High-priority only
                ["INFO", "LOW"],  # Low-priority only
                ["MEDIUM", "HIGH", "CRITICAL"],  # Exclude INFO/LOW
            ]
        ),
    ] = ["MEDIUM", "HIGH", "CRITICAL"],
) -> dict[str, Any]:
    """List detections with comprehensive filtering support."""
```

## Anti-Patterns to Avoid

### 1. The God Tool Anti-Pattern

```python
# ❌ Don't create tools that do everything
@mcp.tool
async def manage_everything(
    resource_type: str,
    action: str,
    resource_id: str = None,
    filters: dict = None,
    updates: dict = None,
    **kwargs
) -> dict[str, Any]:
    """Manage any resource with any action."""  # Too generic!
```

### 2. The Inconsistent Response Anti-Pattern

```python
# ❌ Don't use different response formats
@mcp.tool
async def get_alert(alert_id: str) -> dict:
    return {"alert": {...}}  # Inconsistent with other tools

@mcp.tool  
async def get_detection(detection_id: str) -> dict:
    return {"success": True, "detection": {...}}  # Different format
```

### 3. The Magic Parameter Anti-Pattern

```python
# ❌ Don't use unclear parameter names or formats
@mcp.tool
async def list_items(
    filters: str,  # What format? JSON? CSV?
    opts: dict,    # What options are valid?
    mode: int,     # What do the numbers mean?
) -> dict[str, Any]:
    """List items with mysterious parameters."""
```

## Summary

These patterns provide a foundation for building consistent, user-friendly, and maintainable MCP tools. Key principles:

1. **Consistency**: Use the same patterns across all tools
2. **Clarity**: Make tool purpose and parameters obvious
3. **Robustness**: Handle errors gracefully and provide useful feedback
4. **Performance**: Consider response times and resource usage
5. **Security**: Validate inputs and check permissions
6. **Documentation**: Provide comprehensive examples and descriptions

## Related Documentation

- [MCP Development Best Practices](./mcp-development-best-practices.md)
- [MCP Testing Guide](./mcp-testing-guide.md)
- [FastMCP Documentation](https://gofastmcp.com/)