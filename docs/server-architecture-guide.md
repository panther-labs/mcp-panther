# MCP Server Architecture Guide

This guide covers the architecture patterns and context management strategies for building robust MCP servers with FastMCP, based on the Panther MCP server implementation and FastMCP best practices.

## Table of Contents

- [Server Architecture Overview](#server-architecture-overview)
- [Component Organization](#component-organization)
- [Context Management](#context-management)
- [Server Composition](#server-composition)
- [Transport Protocols](#transport-protocols)
- [Middleware Patterns](#middleware-patterns)
- [State Management](#state-management)
- [Logging and Monitoring](#logging-and-monitoring)
- [Configuration Management](#configuration-management)

## Server Architecture Overview

### Core Components

```
FastMCP Server
├── Tools (Functions callable by LLMs)
├── Resources (Static/dynamic content providers)
├── Prompts (Reusable message templates)
├── Context (Request-scoped capabilities)
├── Middleware (Cross-cutting concerns)
└── Transport (STDIO, HTTP, SSE)
```

### Basic Server Structure

```python
# server.py
import logging
import sys
from fastmcp import FastMCP
from .panther_mcp_core import register_all_components

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)

def create_server() -> FastMCP:
    """Create and configure the MCP server."""
    
    # Create server instance
    mcp = FastMCP(
        name="panther-mcp-server",
        instructions="Provides Panther security platform integration capabilities",
        tags=["security", "siem", "panther"]
    )
    
    # Register all components
    register_all_components(mcp)
    
    return mcp

def main():
    """Main entry point."""
    mcp = create_server()
    mcp.run()

if __name__ == "__main__":
    main()
```

## Component Organization

### 1. Modular Component Structure

Organize components by functional domain:

```
src/mcp_panther/panther_mcp_core/
├── __init__.py                 # Component registration
├── tools/                      # Tool implementations
│   ├── __init__.py
│   ├── registry.py            # Tool decorator
│   ├── alerts.py              # Alert management tools
│   ├── detections.py          # Detection management tools
│   ├── data_lake.py           # Data lake query tools
│   ├── users.py               # User management tools
│   └── ...
├── resources/                  # Resource providers
│   ├── __init__.py
│   ├── registry.py            # Resource decorator
│   └── config.py              # Configuration resources
├── prompts/                    # Prompt templates
│   ├── __init__.py
│   ├── registry.py            # Prompt decorator
│   └── alert_triage.py        # Alert analysis prompts
└── client/                     # External API integration
    ├── __init__.py
    ├── panther_client.py       # GraphQL client
    └── queries.py              # GraphQL queries
```

### 2. Component Registration Pattern

Centralized component registration:

```python
# panther_mcp_core/__init__.py
from fastmcp import FastMCP
from . import tools, resources, prompts

def register_all_components(mcp: FastMCP) -> None:
    """Register all MCP components with the server."""
    
    # Register tools
    tools.register_tools(mcp)
    
    # Register resources  
    resources.register_resources(mcp)
    
    # Register prompts
    prompts.register_prompts(mcp)

# tools/__init__.py
from fastmcp import FastMCP
from . import alerts, detections, data_lake, users

def register_tools(mcp: FastMCP) -> None:
    """Register all tool modules."""
    
    # Import modules to trigger decorator registration
    alerts.register_alert_tools(mcp)
    detections.register_detection_tools(mcp)
    data_lake.register_data_lake_tools(mcp)
    users.register_user_tools(mcp)

# tools/alerts.py
from .registry import mcp_tool

def register_alert_tools(mcp):
    """Register alert-related tools."""
    
    # Tools are auto-registered via decorators when module is imported
    pass

@mcp_tool
async def get_alert(alert_id: str) -> dict:
    """Get alert information."""
    # Implementation
```

### 3. Registry Pattern for Decorators

Custom decorators for component registration:

```python
# tools/registry.py
from typing import Callable, Any
from fastmcp import FastMCP

# Global registry to collect decorated functions
_tool_registry: list[Callable] = []

def mcp_tool(func: Callable) -> Callable:
    """Decorator to register MCP tools."""
    _tool_registry.append(func)
    return func

def register_tools(mcp: FastMCP) -> None:
    """Register all collected tools with MCP server."""
    for tool_func in _tool_registry:
        mcp.tool(tool_func)

# Usage
@mcp_tool
async def my_tool() -> dict:
    """Tool implementation."""
    pass
```

## Context Management

### 1. Context Access Patterns

FastMCP provides two ways to access context:

#### Dependency Injection (Recommended)

```python
from fastmcp import Context

@mcp.tool
async def process_with_logging(
    data: str,
    ctx: Context,  # Context injected as parameter
) -> dict[str, Any]:
    """Tool that uses context for logging and progress."""
    
    await ctx.info(f"Starting processing of {len(data)} characters")
    
    try:
        # Simulate long operation with progress reporting
        for i in range(0, len(data), 100):
            chunk = data[i:i+100]
            await ctx.report_progress(
                current=i + len(chunk),
                total=len(data),
                description=f"Processing chunk {i//100 + 1}"
            )
            
            # Process chunk
            await process_chunk(chunk)
        
        await ctx.info("Processing completed successfully")
        
        return {
            "success": True,
            "processed_length": len(data)
        }
        
    except Exception as e:
        await ctx.error(f"Processing failed: {str(e)}")
        raise
```

#### Dependency Function (For Nested Calls)

```python
from fastmcp import get_context

async def helper_function(data: str) -> str:
    """Helper function that needs context access."""
    
    ctx = get_context()  # Get context from current request
    await ctx.debug(f"Processing data in helper: {len(data)} chars")
    
    # Process data
    result = process_data(data)
    
    await ctx.debug("Helper processing complete")
    return result

@mcp.tool
async def main_tool(input_data: str) -> dict[str, Any]:
    """Main tool that calls helper functions."""
    
    # Helper functions can access context automatically
    processed = await helper_function(input_data)
    
    return {
        "success": True,
        "result": processed
    }
```

### 2. Context Capabilities

#### Logging

```python
@mcp.tool
async def detailed_operation(ctx: Context) -> dict[str, Any]:
    """Demonstrate all logging levels."""
    
    await ctx.debug("Debug: Starting detailed operation")
    await ctx.info("Info: Operation parameters validated")
    await ctx.warning("Warning: Using default timeout value")
    await ctx.error("Error: Retrying failed request")
    
    return {"success": True}
```

#### Progress Reporting

```python
@mcp.tool
async def batch_processor(
    items: list[str],
    ctx: Context,
) -> dict[str, Any]:
    """Process items with progress reporting."""
    
    results = []
    total_items = len(items)
    
    for i, item in enumerate(items):
        # Report progress
        await ctx.report_progress(
            current=i + 1,
            total=total_items,
            description=f"Processing item: {item}"
        )
        
        # Process item
        result = await process_item(item)
        results.append(result)
        
        # Log milestones
        if (i + 1) % 10 == 0:
            await ctx.info(f"Completed {i + 1}/{total_items} items")
    
    return {
        "success": True,
        "processed_count": len(results),
        "results": results
    }
```

#### State Management

```python
@mcp.tool
async def stateful_operation(
    operation_id: str,
    ctx: Context,
) -> dict[str, Any]:
    """Use context state for request-scoped data sharing."""
    
    # Store operation metadata
    ctx.set_state("operation_id", operation_id)
    ctx.set_state("start_time", time.time())
    
    # Process with helper functions that can access state
    result = await process_with_state()
    
    # Calculate duration
    start_time = ctx.get_state("start_time")
    duration = time.time() - start_time
    
    return {
        "success": True,
        "operation_id": operation_id,
        "duration_seconds": duration,
        "result": result
    }

async def process_with_state() -> str:
    """Helper that accesses shared state."""
    
    ctx = get_context()
    operation_id = ctx.get_state("operation_id")
    
    await ctx.info(f"Processing operation {operation_id}")
    
    # Implementation
    return "processed"
```

## Server Composition

### 1. Multi-Server Composition

Combine multiple specialized servers:

```python
from fastmcp import FastMCP

def create_alert_server() -> FastMCP:
    """Server focused on alert management."""
    mcp = FastMCP(name="panther-alerts")
    # Register alert-specific tools
    return mcp

def create_detection_server() -> FastMCP:
    """Server focused on detection management."""
    mcp = FastMCP(name="panther-detections")
    # Register detection-specific tools
    return mcp

def create_composite_server() -> FastMCP:
    """Composite server combining functionality."""
    
    # Create main server
    main_server = FastMCP(name="panther-composite")
    
    # Create specialized servers
    alert_server = create_alert_server()
    detection_server = create_detection_server()
    
    # Compose servers (if supported by FastMCP)
    # This pattern may vary based on FastMCP version
    
    return main_server
```

### 2. Modular Registration

Register components conditionally:

```python
def create_server(enabled_modules: list[str] = None) -> FastMCP:
    """Create server with selective module loading."""
    
    if enabled_modules is None:
        enabled_modules = ["alerts", "detections", "data_lake"]
    
    mcp = FastMCP(name="panther-mcp-server")
    
    # Register modules based on configuration
    if "alerts" in enabled_modules:
        from .tools import alerts
        alerts.register_alert_tools(mcp)
    
    if "detections" in enabled_modules:
        from .tools import detections
        detections.register_detection_tools(mcp)
    
    if "data_lake" in enabled_modules:
        from .tools import data_lake
        data_lake.register_data_lake_tools(mcp)
    
    return mcp
```

## Transport Protocols

### 1. STDIO Transport (Default)

Standard input/output transport for MCP clients:

```python
def main():
    """Run server with STDIO transport."""
    mcp = create_server()
    
    # Default transport is STDIO
    mcp.run()  # Reads from stdin, writes to stdout
```

### 2. HTTP Transport

HTTP-based transport for web integration:

```python
def main():
    """Run server with HTTP transport."""
    mcp = create_server()
    
    # Configure for HTTP transport
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8000
    )
```

### 3. Environment-Based Transport Selection

```python
import os

def main():
    """Run server with transport from environment."""
    mcp = create_server()
    
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "3000"))
    
    if transport == "streamable-http":
        mcp.run(
            transport=transport,
            host=host,
            port=port
        )
    else:
        mcp.run()  # Default STDIO
```

## Middleware Patterns

### 1. Request Logging Middleware

```python
from fastmcp import Context
import time
import logging

logger = logging.getLogger(__name__)

async def logging_middleware(ctx: Context, call_next):
    """Log all tool calls with timing."""
    
    start_time = time.time()
    
    # Get request information
    tool_name = getattr(ctx, 'tool_name', 'unknown')
    
    logger.info(f"Starting tool call: {tool_name}")
    
    try:
        # Call the actual tool
        result = await call_next()
        
        duration = time.time() - start_time
        logger.info(f"Tool {tool_name} completed in {duration:.2f}s")
        
        return result
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Tool {tool_name} failed after {duration:.2f}s: {str(e)}")
        raise

# Register middleware with server
def create_server() -> FastMCP:
    mcp = FastMCP(name="panther-mcp-server")
    
    # Register middleware (syntax may vary by FastMCP version)
    # mcp.middleware(logging_middleware)
    
    return mcp
```

### 2. Authentication Middleware

```python
async def auth_middleware(ctx: Context, call_next):
    """Validate API token for all requests."""
    
    # Check for valid authentication
    api_token = os.getenv("PANTHER_API_TOKEN")
    instance_url = os.getenv("PANTHER_INSTANCE_URL")
    
    if not api_token or not instance_url:
        raise ValueError("Missing required authentication configuration")
    
    # Store auth info in context for tools to use
    ctx.set_state("api_token", api_token)
    ctx.set_state("instance_url", instance_url)
    
    # Proceed with request
    return await call_next()
```

### 3. Error Handling Middleware

```python
async def error_handling_middleware(ctx: Context, call_next):
    """Global error handling for all tools."""
    
    try:
        return await call_next()
        
    except PermissionError:
        return {
            "success": False,
            "error": "Insufficient permissions for this operation",
            "error_code": "PERMISSION_DENIED"
        }
    except ConnectionError:
        return {
            "success": False,
            "error": "Unable to connect to Panther API",
            "error_code": "CONNECTION_ERROR"
        }
    except Exception as e:
        logger.exception("Unexpected error in tool execution")
        return {
            "success": False,
            "error": "An unexpected error occurred",
            "error_code": "INTERNAL_ERROR"
        }
```

## State Management

### 1. Request-Scoped State

Use context state for data sharing within a single request:

```python
@mcp.tool
async def multi_step_operation(
    input_data: str,
    ctx: Context,
) -> dict[str, Any]:
    """Operation with multiple steps sharing state."""
    
    # Initialize shared state
    ctx.set_state("input_data", input_data)
    ctx.set_state("step_results", [])
    
    # Step 1
    step1_result = await execute_step1()
    
    # Step 2 can access state from step 1
    step2_result = await execute_step2()
    
    # Get accumulated results
    all_results = ctx.get_state("step_results")
    
    return {
        "success": True,
        "steps_completed": len(all_results),
        "results": all_results
    }

async def execute_step1() -> str:
    """Step that updates shared state."""
    ctx = get_context()
    
    input_data = ctx.get_state("input_data")
    result = f"Step 1 processed: {input_data}"
    
    # Update shared state
    results = ctx.get_state("step_results")
    results.append(result)
    ctx.set_state("step_results", results)
    
    return result
```

### 2. Client Connection State

Manage client-specific information:

```python
class ClientStateManager:
    """Manage per-client state across requests."""
    
    def __init__(self):
        self.client_sessions = {}
    
    async def get_client_info(self, ctx: Context) -> dict:
        """Get client information from context."""
        
        # Extract client identifier (implementation depends on FastMCP)
        client_id = getattr(ctx, 'client_id', 'default')
        
        if client_id not in self.client_sessions:
            self.client_sessions[client_id] = {
                "created_at": time.time(),
                "request_count": 0,
                "last_activity": time.time()
            }
        
        session = self.client_sessions[client_id]
        session["request_count"] += 1
        session["last_activity"] = time.time()
        
        return session

# Global state manager
client_state = ClientStateManager()

@mcp.tool
async def get_session_info(ctx: Context) -> dict[str, Any]:
    """Get current session information."""
    
    session = await client_state.get_client_info(ctx)
    
    return {
        "success": True,
        "session": session
    }
```

## Logging and Monitoring

### 1. Structured Logging

```python
import logging
import json
from typing import Any

class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in log_data and not key.startswith('_'):
                log_data[key] = value
        
        return json.dumps(log_data)

# Configure structured logging
def setup_logging():
    """Configure structured logging for the server."""
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(StructuredFormatter())
    
    logger.addHandler(handler)
```

### 2. Tool Performance Monitoring

```python
import functools
import time
from typing import Callable, Any

def monitor_performance(func: Callable) -> Callable:
    """Decorator to monitor tool performance."""
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        tool_name = func.__name__
        
        try:
            result = await func(*args, **kwargs)
            
            duration = time.time() - start_time
            
            # Log performance metrics
            logger.info(
                "Tool execution completed",
                extra={
                    "tool_name": tool_name,
                    "duration_seconds": duration,
                    "status": "success"
                }
            )
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            
            logger.error(
                "Tool execution failed",
                extra={
                    "tool_name": tool_name,
                    "duration_seconds": duration,
                    "status": "error",
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            )
            
            raise
    
    return wrapper

# Usage
@monitor_performance
@mcp.tool
async def monitored_tool() -> dict[str, Any]:
    """Tool with performance monitoring."""
    # Implementation
    pass
```

## Configuration Management

### 1. Environment-Based Configuration

```python
import os
from typing import Optional
from pydantic import BaseSettings

class ServerConfig(BaseSettings):
    """Server configuration from environment variables."""
    
    # Panther API configuration
    panther_instance_url: str
    panther_api_token: str
    
    # Server configuration
    server_name: str = "panther-mcp-server"
    log_level: str = "INFO"
    
    # Transport configuration
    transport: str = "stdio"
    host: str = "127.0.0.1"
    port: int = 3000
    
    # Feature flags
    enable_caching: bool = False
    enable_metrics: bool = True
    
    class Config:
        env_prefix = "MCP_"
        case_sensitive = False

# Global configuration
config = ServerConfig()

def create_server() -> FastMCP:
    """Create server using configuration."""
    
    mcp = FastMCP(
        name=config.server_name,
        instructions="Panther security platform integration",
    )
    
    # Configure logging level
    logging.getLogger().setLevel(getattr(logging, config.log_level.upper()))
    
    # Register components based on configuration
    register_components(mcp, config)
    
    return mcp
```

### 2. Dynamic Configuration

```python
@mcp.resource("config://panther")
def get_server_config() -> dict[str, Any]:
    """Provide current server configuration to clients."""
    
    return {
        "server_name": config.server_name,
        "panther_instance": config.panther_instance_url,
        "features": {
            "caching_enabled": config.enable_caching,
            "metrics_enabled": config.enable_metrics,
        },
        "transport": {
            "type": config.transport,
            "host": config.host if config.transport == "http" else None,
            "port": config.port if config.transport == "http" else None,
        }
    }
```

## Deployment Patterns

### 1. Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen

# Copy source code
COPY src/ ./src/

# Set environment variables
ENV MCP_TRANSPORT=streamable-http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000

# Expose port
EXPOSE 8000

# Run server
CMD ["uv", "run", "python", "-m", "mcp_panther.server"]
```

### 2. Process Management

```python
import signal
import asyncio
from typing import Optional

class GracefulServer:
    """Server with graceful shutdown handling."""
    
    def __init__(self):
        self.mcp: Optional[FastMCP] = None
        self.shutdown_event = asyncio.Event()
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        
        def signal_handler(signum, frame):
            print(f"Received signal {signum}, initiating graceful shutdown...")
            self.shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def run(self):
        """Run server with graceful shutdown."""
        
        self.setup_signal_handlers()
        self.mcp = create_server()
        
        try:
            # Start server (this would be adapted to FastMCP's async interface)
            await self.mcp.serve_async()
            
        except KeyboardInterrupt:
            print("Shutdown initiated by user")
        
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Cleanup resources during shutdown."""
        print("Cleaning up resources...")
        
        # Close database connections, cleanup temp files, etc.
        if self.mcp:
            # Cleanup MCP server resources
            pass
        
        print("Graceful shutdown complete")

def main():
    """Main entry point with graceful shutdown."""
    server = GracefulServer()
    asyncio.run(server.run())
```

## Best Practices Summary

1. **Modular Architecture**: Organize components by domain/functionality
2. **Registry Pattern**: Use centralized component registration
3. **Context Usage**: Leverage context for logging, progress, and state
4. **Transport Flexibility**: Support multiple transport protocols
5. **Structured Logging**: Use JSON logging for better observability
6. **Configuration Management**: Environment-based configuration with validation
7. **Graceful Shutdown**: Handle shutdown signals properly
8. **Performance Monitoring**: Track tool execution metrics
9. **Error Handling**: Implement comprehensive error handling patterns
10. **Testing Architecture**: Design for testability with dependency injection

## Related Documentation

- [MCP Development Best Practices](./mcp-development-best-practices.md)
- [Tool Design Patterns](./tool-design-patterns.md)
- [MCP Testing Guide](./mcp-testing-guide.md)
- [FastMCP Documentation](https://gofastmcp.com/)
