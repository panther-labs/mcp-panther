# MCP Server Testing Guide

This guide provides comprehensive testing strategies for Model Context Protocol (MCP) servers using FastMCP, based on official documentation and proven practices from the Panther MCP server.

## Table of Contents

- [Testing Philosophy](#testing-philosophy)
- [Setup and Configuration](#setup-and-configuration)
- [Testing Strategies](#testing-strategies)
- [Test Patterns](#test-patterns)
- [Integration Testing](#integration-testing)
- [Mocking and Fixtures](#mocking-and-fixtures)
- [Performance Testing](#performance-testing)
- [Error Scenario Testing](#error-scenario-testing)
- [Continuous Integration](#continuous-integration)

## Testing Philosophy

### Core Principles

1. **Test Thoroughly**: Every tool function should have comprehensive test coverage
2. **Test Realistically**: Use realistic data and scenarios that mirror production usage
3. **Test Edge Cases**: Include error conditions, boundary values, and failure scenarios
4. **Test Fast**: Use in-memory testing for speed and reliability
5. **Test Independently**: Each test should be independent and repeatable

### Testing Pyramid for MCP Servers

```
    ┌─── End-to-End Tests ───┐
    │   (Full MCP Protocol)  │
    ├─── Integration Tests ───┤
    │   (Tool + External API) │
    ├──── Unit Tests ────────┤
    │   (Individual Tools)    │
    └─── Component Tests ────┘
         (Business Logic)
```

## Setup and Configuration

### pytest Configuration

Create a `pytest.ini` or `pyproject.toml` configuration:

```ini
# pytest.ini
[tool:pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_functions = test_*
addopts = 
    --verbose
    --tb=short
    --cov=src
    --cov-report=html
    --cov-report=term-missing
```

### Test Dependencies

Install testing dependencies:

```bash
# Via uv (recommended)
uv add --group dev pytest pytest-asyncio pytest-cov fastmcp

# Via pip
pip install pytest pytest-asyncio pytest-cov fastmcp
```

### Environment Setup

Configure test environment variables:

```python
# conftest.py
import os
import pytest
from fastmcp import FastMCP
from unittest.mock import AsyncMock

# Set test environment variables
os.environ["PANTHER_INSTANCE_URL"] = "https://test-instance.panther.io"
os.environ["PANTHER_API_TOKEN"] = "test-token-12345"

@pytest.fixture
def mcp_server():
    """Create a test MCP server instance."""
    from src.mcp_panther.server import create_server
    return create_server()

@pytest.fixture
def mock_graphql_client():
    """Mock GraphQL client for external API calls."""
    return AsyncMock()
```

## Testing Strategies

### 1. In-Memory Testing (Recommended)

The most efficient approach - directly pass the FastMCP server instance to a Client:

```python
import pytest
from fastmcp import Client

@pytest.mark.asyncio
async def test_get_alert_success(mcp_server):
    """Test successful alert retrieval."""
    async with Client(mcp_server) as client:
        # Call the tool directly
        result = await client.call_tool("get_alert", {"alert_id": "test-alert-123"})
        
        # Verify the response
        assert result.is_success
        data = result.data
        assert data["success"] is True
        assert "alert" in data
        assert data["alert"]["id"] == "test-alert-123"

@pytest.mark.asyncio
async def test_get_alert_not_found(mcp_server):
    """Test alert not found scenario."""
    async with Client(mcp_server) as client:
        result = await client.call_tool("get_alert", {"alert_id": "nonexistent"})
        
        assert result.is_success  # Tool executed successfully
        data = result.data
        assert data["success"] is False
        assert "error" in data
        assert "not found" in data["error"].lower()
```

### 2. Mocking External Dependencies

Mock external API calls and database connections:

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
@patch('src.mcp_panther.panther_mcp_core.client.PantherMCPClient.execute_query')
async def test_list_alerts_with_mock(mock_execute, mcp_server):
    """Test alert listing with mocked GraphQL client."""
    # Setup mock response
    mock_execute.return_value = {
        "alerts": {
            "alertList": [
                {
                    "id": "alert-1",
                    "title": "Test Alert",
                    "severity": "HIGH",
                    "status": "OPEN"
                }
            ],
            "totalCount": 1
        }
    }
    
    async with Client(mcp_server) as client:
        result = await client.call_tool("list_alerts", {
            "severities": ["HIGH"],
            "page_size": 10
        })
        
        # Verify the tool was called correctly
        assert result.is_success
        data = result.data
        assert data["success"] is True
        assert len(data["alerts"]) == 1
        assert data["alerts"][0]["severity"] == "HIGH"
        
        # Verify the GraphQL client was called
        mock_execute.assert_called_once()
```

### 3. Fixture-Based Testing

Create reusable test fixtures for common scenarios:

```python
# conftest.py
@pytest.fixture
def sample_alert():
    """Sample alert data for testing."""
    return {
        "id": "alert-test-123",
        "title": "Suspicious Login Activity",
        "severity": "HIGH",
        "status": "OPEN",
        "createdAt": "2024-01-15T10:30:00Z",
        "assignee": None,
        "rule": {
            "id": "rule-123",
            "name": "Failed Login Detection"
        }
    }

@pytest.fixture
def sample_alerts_response(sample_alert):
    """Sample GraphQL response for alerts query."""
    return {
        "alerts": {
            "alertList": [sample_alert],
            "totalCount": 1,
            "hasNextPage": False
        }
    }

# test_alerts.py
@pytest.mark.asyncio
async def test_get_alert_with_fixture(mcp_server, sample_alert, mock_graphql_client):
    """Test alert retrieval using fixtures."""
    mock_graphql_client.execute_query.return_value = {
        "alerts": {"alertList": [sample_alert]}
    }
    
    async with Client(mcp_server) as client:
        result = await client.call_tool("get_alert", {"alert_id": sample_alert["id"]})
        
        assert result.is_success
        data = result.data
        assert data["alert"]["title"] == sample_alert["title"]
```

## Test Patterns

### 1. AAA Pattern (Arrange, Act, Assert)

Structure tests with clear sections:

```python
@pytest.mark.asyncio
async def test_update_alert_status(mcp_server, sample_alert):
    """Test alert status update."""
    # Arrange
    alert_id = sample_alert["id"]
    new_status = "RESOLVED"
    
    with patch('src.mcp_panther.panther_mcp_core.client.PantherMCPClient.execute_query') as mock_execute:
        mock_execute.return_value = {
            "updateAlertStatus": {
                "alertIds": [alert_id]
            }
        }
        
        # Act
        async with Client(mcp_server) as client:
            result = await client.call_tool("update_alert_status", {
                "alert_ids": [alert_id],
                "status": new_status
            })
        
        # Assert
        assert result.is_success
        data = result.data
        assert data["success"] is True
        assert alert_id in data["alerts"]
        mock_execute.assert_called_once()
```

### 2. Parameterized Testing

Test multiple scenarios with parameters:

```python
@pytest.mark.parametrize("severity,expected_count", [
    (["CRITICAL"], 2),
    (["HIGH"], 5),
    (["MEDIUM", "LOW"], 10),
    (["CRITICAL", "HIGH", "MEDIUM", "LOW"], 17),
])
@pytest.mark.asyncio
async def test_list_alerts_by_severity(mcp_server, severity, expected_count):
    """Test alert filtering by different severities."""
    with patch('src.mcp_panther.panther_mcp_core.client.PantherMCPClient.execute_query') as mock_execute:
        mock_execute.return_value = {
            "alerts": {
                "alertList": [{"id": f"alert-{i}"} for i in range(expected_count)],
                "totalCount": expected_count
            }
        }
        
        async with Client(mcp_server) as client:
            result = await client.call_tool("list_alerts", {"severities": severity})
            
        data = result.data
        assert len(data["alerts"]) == expected_count
```

### 3. Error Scenario Testing

Comprehensive error condition testing:

```python
@pytest.mark.parametrize("error_type,expected_message", [
    ("NOT_FOUND", "Alert with ID 'nonexistent' not found"),
    ("PERMISSION_DENIED", "Insufficient permissions"),
    ("INVALID_INPUT", "Alert ID cannot be empty"),
])
@pytest.mark.asyncio
async def test_get_alert_error_scenarios(mcp_server, error_type, expected_message):
    """Test various error scenarios for get_alert."""
    with patch('src.mcp_panther.panther_mcp_core.client.PantherMCPClient.execute_query') as mock_execute:
        
        if error_type == "NOT_FOUND":
            mock_execute.side_effect = AlertNotFoundError("Alert not found")
            alert_id = "nonexistent"
        elif error_type == "PERMISSION_DENIED":
            mock_execute.side_effect = PermissionError("Access denied")
            alert_id = "restricted-alert"
        else:  # INVALID_INPUT
            alert_id = ""
        
        async with Client(mcp_server) as client:
            result = await client.call_tool("get_alert", {"alert_id": alert_id})
            
        data = result.data
        assert data["success"] is False
        assert expected_message in data["error"]
```

## Integration Testing

### 1. End-to-End Tool Testing

Test complete tool workflows:

```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_alert_management_workflow(mcp_server):
    """Test complete alert management workflow."""
    
    async with Client(mcp_server) as client:
        # 1. List alerts
        alerts_result = await client.call_tool("list_alerts", {"page_size": 5})
        assert alerts_result.is_success
        alerts = alerts_result.data["alerts"]
        
        if alerts:
            alert_id = alerts[0]["id"]
            
            # 2. Get specific alert
            alert_result = await client.call_tool("get_alert", {"alert_id": alert_id})
            assert alert_result.is_success
            
            # 3. Add comment
            comment_result = await client.call_tool("add_alert_comment", {
                "alert_id": alert_id,
                "comment": "Test comment from integration test"
            })
            assert comment_result.is_success
            
            # 4. Update status
            status_result = await client.call_tool("update_alert_status", {
                "alert_ids": [alert_id],
                "status": "TRIAGED"
            })
            assert status_result.is_success
```

### 2. Cross-Tool Integration

Test interactions between multiple tools:

```python
@pytest.mark.asyncio
async def test_detection_and_alert_integration(mcp_server):
    """Test integration between detection and alert tools."""
    
    async with Client(mcp_server) as client:
        # Get a detection
        detection_result = await client.call_tool("get_detection", {
            "detection_id": "AWS.Suspicious.Activity"
        })
        assert detection_result.is_success
        
        detection = detection_result.data["detection"]
        
        # Find alerts for this detection
        alerts_result = await client.call_tool("list_alerts", {
            "detection_id": detection["id"],
            "page_size": 10
        })
        assert alerts_result.is_success
        
        # Verify alert-detection relationship
        alerts = alerts_result.data["alerts"]
        for alert in alerts:
            assert alert["rule"]["id"] == detection["id"]
```

## Performance Testing

### 1. Response Time Testing

Measure tool execution times:

```python
import time
import pytest

@pytest.mark.asyncio
async def test_query_performance(mcp_server):
    """Test data lake query performance."""
    
    start_time = time.time()
    
    async with Client(mcp_server) as client:
        result = await client.call_tool("query_data_lake", {
            "sql": "SELECT COUNT(*) FROM panther_logs.public.aws_cloudtrail WHERE p_event_time > CURRENT_TIMESTAMP - INTERVAL '1 DAY'"
        })
    
    execution_time = time.time() - start_time
    
    assert result.is_success
    assert execution_time < 5.0  # Should complete within 5 seconds
```

### 2. Load Testing

Test with multiple concurrent requests:

```python
import asyncio
import pytest

@pytest.mark.asyncio
async def test_concurrent_requests(mcp_server):
    """Test handling of concurrent tool calls."""
    
    async def make_request(client, alert_id):
        return await client.call_tool("get_alert", {"alert_id": alert_id})
    
    async with Client(mcp_server) as client:
        # Make 10 concurrent requests
        tasks = [
            make_request(client, f"alert-{i}")
            for i in range(10)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all requests completed
        assert len(results) == 10
        for result in results:
            assert not isinstance(result, Exception)
```

## Mocking and Fixtures

### 1. GraphQL Client Mocking

```python
# conftest.py
@pytest.fixture
def mock_panther_client():
    """Mock Panther GraphQL client."""
    with patch('src.mcp_panther.panther_mcp_core.client.PantherMCPClient') as mock:
        client_instance = AsyncMock()
        mock.return_value = client_instance
        yield client_instance

# Usage in tests
@pytest.mark.asyncio
async def test_with_mock_client(mcp_server, mock_panther_client):
    """Test using mocked Panther client."""
    mock_panther_client.execute_query.return_value = {"test": "data"}
    
    async with Client(mcp_server) as client:
        result = await client.call_tool("some_tool", {})
        
    mock_panther_client.execute_query.assert_called_once()
```

### 2. Environment Variable Mocking

```python
@pytest.fixture
def mock_environment():
    """Mock environment variables for testing."""
    with patch.dict(os.environ, {
        "PANTHER_INSTANCE_URL": "https://test.panther.io",
        "PANTHER_API_TOKEN": "test-token",
    }):
        yield

@pytest.mark.asyncio
async def test_with_mock_env(mcp_server, mock_environment):
    """Test with mocked environment."""
    # Test runs with test environment variables
    pass
```

## Error Scenario Testing

### 1. Network Failure Simulation

```python
@pytest.mark.asyncio
async def test_network_failure_handling(mcp_server):
    """Test handling of network failures."""
    
    with patch('src.mcp_panther.panther_mcp_core.client.PantherMCPClient.execute_query') as mock_execute:
        mock_execute.side_effect = ConnectionError("Network unavailable")
        
        async with Client(mcp_server) as client:
            result = await client.call_tool("list_alerts", {})
            
        data = result.data
        assert data["success"] is False
        assert "network" in data["error"].lower() or "connection" in data["error"].lower()
```

### 2. API Rate Limiting

```python
@pytest.mark.asyncio
async def test_rate_limit_handling(mcp_server):
    """Test handling of API rate limits."""
    
    with patch('src.mcp_panther.panther_mcp_core.client.PantherMCPClient.execute_query') as mock_execute:
        mock_execute.side_effect = RateLimitError("Rate limit exceeded")
        
        async with Client(mcp_server) as client:
            result = await client.call_tool("list_alerts", {})
            
        data = result.data
        assert data["success"] is False
        assert "rate limit" in data["error"].lower()
```

## Continuous Integration

### 1. GitHub Actions Configuration

```yaml
# .github/workflows/test.yml
name: Test MCP Server

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    
    - name: Install UV
      run: pip install uv
    
    - name: Install dependencies
      run: uv sync --group dev
    
    - name: Run tests
      run: uv run pytest
      env:
        PANTHER_INSTANCE_URL: ${{ secrets.TEST_PANTHER_URL }}
        PANTHER_API_TOKEN: ${{ secrets.TEST_PANTHER_TOKEN }}
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

### 2. Test Organization

```
tests/
├── conftest.py                 # Shared fixtures
├── unit/                       # Unit tests
│   ├── test_tools/
│   │   ├── test_alerts.py
│   │   ├── test_detections.py
│   │   └── test_data_lake.py
│   └── test_client.py
├── integration/                # Integration tests
│   ├── test_workflows.py
│   └── test_cross_tool.py
└── performance/                # Performance tests
    ├── test_load.py
    └── test_response_times.py
```

## Running Tests

### Local Development

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/unit/test_tools/test_alerts.py

# Run tests with coverage
uv run pytest --cov=src --cov-report=html

# Run only fast tests (skip integration)
uv run pytest -m "not integration"

# Run with verbose output
uv run pytest -v
```

### Integration Tests

```bash
# Run integration tests (requires valid credentials)
uv run pytest -m integration

# Run with real Panther instance
PANTHER_INSTANCE_URL=https://your-instance.panther.io \
PANTHER_API_TOKEN=your-token \
uv run pytest tests/integration/
```

## Best Practices Summary

1. **Use In-Memory Testing**: FastMCP's direct server passing is fastest and most reliable
2. **Mock External Dependencies**: Mock GraphQL clients and external APIs
3. **Test Error Scenarios**: Include comprehensive error condition testing
4. **Use Fixtures**: Create reusable test data and configuration
5. **Test Realistically**: Use realistic data that mirrors production
6. **Measure Performance**: Include response time and load testing
7. **Organize Tests**: Structure tests logically by functionality and scope
8. **Automate Testing**: Use CI/CD for automated test execution

## Related Documentation

- [MCP Development Best Practices](./mcp-development-best-practices.md)
- [Tool Design Patterns](./tool-design-patterns.md)
- [FastMCP Testing Documentation](https://gofastmcp.com/patterns/testing.md)