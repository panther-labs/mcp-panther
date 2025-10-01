# MCP-Panther Release Testing Plan

## Overview

This document outlines the comprehensive testing procedures that must be completed before releasing a new version of mcp-panther. The plan ensures all functionality works correctly and maintains backward compatibility while validating new features and bug fixes.

## Pre-Release Testing Checklist

### 1. Environment Setup

- [ ] Test environment configured with valid Panther instance URL and API token
- [ ] Development dependencies installed (`uv sync --group dev`)
- [ ] Docker environment available for containerized testing
- [ ] Multiple Python versions tested (3.12+)

### 2. Code Quality and Static Analysis

- [ ] All linting checks pass (`make lint`)
- [ ] Code formatting is consistent (`make fmt`)
- [ ] No security vulnerabilities detected
- [ ] Dependencies are up to date and secure

### 3. Unit Testing

- [ ] All existing unit tests pass (`make test`)
- [ ] Test coverage meets minimum requirements (>80%)
- [ ] New functionality has corresponding unit tests
- [ ] Edge cases and error conditions are tested

### 4. Integration Testing

- [ ] FastMCP integration test passes (`make integration-test`)
- [ ] MCP protocol compliance verified
- [ ] Cross-tool interactions work correctly
- [ ] Context management functions properly

### 5. Tool-by-Tool Functional Testing

#### Alert Management Tools

- [ ] `get_alert` - Retrieve single alert by ID
- [ ] `list_alerts` - List alerts with various filters (severity, status, date range)
- [ ] `update_alert_status` - Change alert status (single and bulk)
- [ ] `update_alert_assignee` - Assign alerts to users
- [ ] `add_alert_comment` - Add comments to alerts
- [ ] `list_alert_comments` - Retrieve alert comments
- [ ] `get_alert_events` - Get events for specific alerts
- [ ] `get_alert_event_stats` - Cross-alert event analysis

#### Detection Management Tools

- [ ] `get_detection` - Retrieve detection details (rules, policies, scheduled rules)
- [ ] `list_detections` - List detections with filtering options
- [ ] `disable_detection` - Disable detections of various types

#### Data Lake Tools

- [ ] `query_data_lake` - Execute SQL queries with proper validation
- [ ] `get_table_schema` - Retrieve table structure information
- [ ] `list_databases` - List available databases
- [ ] `list_database_tables` - List tables in specific databases

#### Log Source Tools

- [ ] `list_log_sources` - List log sources with filters
- [ ] `get_http_log_source` - Get HTTP log source configuration

#### Scheduled Query Tools

- [ ] `list_scheduled_queries` - List all scheduled queries
- [ ] `get_scheduled_query` - Get specific scheduled query details

#### Schema Tools

- [ ] `list_log_type_schemas` - List available schemas
- [ ] `get_log_type_schema_details` - Get detailed schema information

#### Global Helper Tools

- [ ] `list_global_helpers` - Alternative global helper listing
- [ ] `get_global_helper` - Alternative global helper retrieval

#### Data Model Tools

- [ ] `list_data_models` - List UDM data models
- [ ] `get_data_model` - Get specific data model details

#### User and Role Management Tools

- [ ] `list_users` - List user accounts
- [ ] `get_user` - Get user details
- [ ] `get_permissions` - Get current user permissions
- [ ] `list_roles` - List available roles
- [ ] `get_role` - Get role details

#### Metrics Tools

- [ ] `get_rule_alert_metrics` - Get alert metrics by rule
- [ ] `get_severity_alert_metrics` - Get alert metrics by severity
- [ ] `get_bytes_processed_per_log_type_and_source` - Get ingestion metrics

### 6. Resource Testing

- [ ] `config://panther` - Configuration resource provides correct information
- [ ] Resource content is properly formatted and accessible

### 7. Prompt Testing

- [ ] Alert triage prompts generate appropriate content
- [ ] Reporting prompts work with context data
- [ ] Prompt parameters are validated correctly

### 8. Transport Protocol Testing

- [ ] STDIO transport works correctly (default)
- [ ] Streamable HTTP transport functions properly
- [ ] Environment variable configuration works
- [ ] Port and host binding work as expected

### 9. Error Handling and Edge Cases

- [ ] Invalid API tokens return appropriate errors
- [ ] Network connectivity issues handled gracefully
- [ ] Rate limiting responses handled correctly
- [ ] Malformed parameters return clear error messages
- [ ] Empty result sets handled properly
- [ ] Large result sets are properly paginated/limited

### 10. Performance Testing

- [ ] Response times are acceptable (<5s for most operations)
- [ ] Memory usage remains stable during extended use
- [ ] Concurrent requests handled appropriately
- [ ] Large data queries don't timeout unexpectedly

### 11. Security Testing

- [ ] Input validation prevents injection attacks
- [ ] Sensitive data is not logged or exposed
- [ ] Permission checks work correctly
- [ ] API tokens are handled securely

### 12. Documentation Testing

- [ ] README examples work correctly
- [ ] Tool descriptions match actual functionality
- [ ] Parameter documentation is accurate
- [ ] Installation instructions are current

### 13. Deployment Testing

- [ ] Docker container builds successfully
- [ ] Docker container runs with environment variables
- [ ] UVX installation works correctly
- [ ] PyPI package structure is correct

### 14. Backward Compatibility Testing

- [ ] Existing tool signatures remain unchanged
- [ ] Previous MCP client configurations still work
- [ ] No breaking changes in public API
- [ ] Deprecated features still function with warnings

### 15. Client Integration Testing

- [ ] Claude Desktop integration works
- [ ] Cursor integration works  
- [ ] Goose CLI integration works
- [ ] Goose Desktop integration works
- [ ] Generic MCP clients can connect

## Testing Execution Process

### Phase 1: Automated Testing

1. Run complete test suite: `make test`
2. Run integration tests: `make integration-test`
3. Verify linting and formatting: `make lint && make fmt`
4. Check Docker build: `make docker`

### Phase 2: Manual Functional Testing

1. Set up test environment with real Panther instance
2. Execute tool-by-tool testing using MCP client
3. Test error scenarios and edge cases
4. Verify new features work as documented
5. Test performance under typical load

### Phase 3: Integration Testing

1. Test with multiple MCP clients
2. Verify transport protocols work correctly
3. Test deployment scenarios (Docker, UVX, direct)
4. Validate documentation examples

### Phase 4: Regression Testing

1. Execute previously failed test cases
2. Verify bug fixes work correctly
3. Ensure no new regressions introduced
4. Test backward compatibility scenarios

## Success Criteria

A release is ready when:

- [ ] All automated tests pass
- [ ] All manual testing checklist items complete
- [ ] Performance meets acceptable thresholds
- [ ] Security review completed
- [ ] Documentation is accurate and complete
- [ ] No critical or high-severity issues remain
- [ ] Backward compatibility maintained

## Test Environment Requirements

### Minimum Test Environment

- Python 3.12+
- Valid Panther instance with test data
- API token with comprehensive permissions:
  - Read Alerts, Manage Alerts
  - View Rules, Manage Rules, Manage Policies
  - Query Data Lake, View Log Sources
  - Read User Info, Read Panther Metrics

### Test Data Requirements

- At least 10 alerts in various states
- Multiple detection types (rules, policies, scheduled rules)
- Various log sources and schemas
- User accounts and roles for testing
- Historical data for metrics testing

## Rollback Plan

If critical issues are discovered post-release:

1. Document the issue and impact
2. Determine if hotfix or rollback is appropriate
3. If rolling back:
   - Revert to previous stable version
   - Update documentation
   - Notify users of temporary rollback
   - Plan remediation for next release

## Post-Release Verification

After release:

- [ ] PyPI package installs correctly
- [ ] Docker image pulls and runs successfully
- [ ] Documentation reflects new version
- [ ] Integration examples work with new version
- [ ] Community can successfully use new features

## Notes

- Testing should be performed by someone other than the primary developer when possible
- All test results should be documented with screenshots or logs
- Any failures must be investigated and resolved before release
- Edge cases and error conditions are especially important to test
- Performance regressions should be investigated even if functionality works
