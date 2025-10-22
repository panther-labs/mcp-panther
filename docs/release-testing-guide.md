# MCP Panther Release Testing Guide

This guide provides systematic testing procedures for AI agents (Claude, Cursor, Goose, etc.) to validate MCP Panther server functionality before releases. Follow these test scenarios to ensure all tools work correctly and provide appropriate feedback.

## Table of Contents

- [Pre-Testing Setup](#pre-testing-setup)
- [Tool Category Testing](#tool-category-testing)
- [Integration Testing Scenarios](#integration-testing-scenarios)
- [Error Handling Validation](#error-handling-validation)
- [Performance Testing](#performance-testing)
- [Release Validation Checklist](#release-validation-checklist)

## Pre-Testing Setup

### 1. Verify Environment

Before starting tests, ensure you have:

```
✓ Valid PANTHER_API_TOKEN with appropriate permissions
✓ Valid PANTHER_INSTANCE_URL (e.g., https://your-instance.panther.io)
✓ MCP server running and accessible
✓ At least read-only access to test data in the Panther instance
```

### 2. Test Server Connectivity

**Test Command**: List available MCP tools to verify connectivity
**Expected Result**: Should return a list of 40+ available tools

### 3. Validate Permissions

**Test Command**: Use `get_permissions` tool
**Expected Result**: Should return your current permissions without errors

## Tool Category Testing

### Alerts Management Tools

#### Basic Alert Operations

**Test Scenario 1: List Recent Alerts**

```
Prompt: "Show me the 10 most recent high-severity alerts from the last 24 hours"
Expected Tools: list_alerts
Expected Result: List of alerts with proper severity filtering and date range
Validation: Check that severities=["HIGH"] and page_size=10 are used
```

**Test Scenario 2: Get Alert Details**

```
Prompt: "Get detailed information about alert [ALERT_ID]"
Expected Tools: get_alert
Expected Result: Complete alert details including metadata, timestamps, rule info
Validation: Verify all alert fields are populated correctly
```

**Test Scenario 3: Alert Status Management**

```
Prompt: "Mark alert [ALERT_ID] as triaged and add a comment explaining the investigation"
Expected Tools: update_alert_status, add_alert_comment
Expected Result: Status updated and comment added successfully
Validation: Both operations complete without errors
```

**Test Scenario 4: Alert Events Analysis**

```
Prompt: "Show me sample events for alert [ALERT_ID] to understand what triggered it"
Expected Tools: get_alert_events
Expected Result: Up to 10 sample events from the alert
Validation: Events should be relevant to the alert and properly formatted
```

**Test Scenario 5: Bulk Alert Operations**

```
Prompt: "Find all critical alerts from yesterday and assign them to user [USER_EMAIL]"
Expected Tools: list_alerts, update_alert_assignee
Expected Result: Alerts filtered correctly and assignee updated in bulk
Validation: Date range filtering and bulk assignment work properly
```

**Test Scenario 6: Bulk Alert Updates with Multiple Operations**

```
Prompt: "Update alerts [ALERT_ID_1], [ALERT_ID_2], and [ALERT_ID_3] to resolved status, assign to [USER_EMAIL], and add comment 'Investigated and resolved'"
Expected Tools: bulk_update_alerts
Expected Result: All three operations (status, assignee, comment) applied to all alerts
Validation: Check successful_operations count, verify no failed_operations
```

**Test Scenario 7: AI Alert Triage Analysis**

```
Prompt: "Start an AI triage analysis for alert [ALERT_ID] to help investigate this incident"
Expected Tools: start_ai_alert_triage
Expected Result: AI-generated triage summary with risk assessment, context, and recommendations
Validation: Triage summary includes analysis of events, entities, and suggested next steps
```

**Test Scenario 8: Retrieve AI Triage Summary**

```
Prompt: "Get the AI triage summary for alert [ALERT_ID] that was previously analyzed"
Expected Tools: get_ai_alert_triage_summary
Expected Result: Previously generated AI triage summary retrieved successfully
Validation: Summary contains stream_id, response_text, and completion status
```

### Detection Management Tools

#### Detection Discovery and Analysis

**Test Scenario 9: Rule Discovery**

```
Prompt: "Show me all enabled AWS-related detection rules with high severity"
Expected Tools: list_detections
Expected Result: Filtered list of AWS detection rules
Validation: Check detection_types=["rules"], severity filtering, and state="enabled"
```

**Test Scenario 10: Detection Details**

```
Prompt: "Get the complete code and configuration for detection rule [RULE_ID]"
Expected Tools: get_detection
Expected Result: Complete rule details including Python code, tests, metadata
Validation: Verify rule body and test cases are included
```

**Test Scenario 11: Policy Analysis**

```
Prompt: "List all cloud security policies that check S3 bucket configurations"
Expected Tools: list_detections
Expected Result: Policies filtered by resource type and detection type
Validation: Check detection_types=["policies"] and resource_types filtering
```

**Test Scenario 12: Detection State Management**

```
Prompt: "Disable the detection rule [RULE_ID] temporarily"
Expected Tools: disable_detection
Expected Result: Rule successfully disabled
Validation: Operation completes successfully with proper permissions
```

### Data Lake Operations

#### Query Execution and Analysis

**Test Scenario 13: Basic Log Querying**

```
Prompt: "Query AWS CloudTrail logs for failed login attempts in the last day"
Expected Tools: query_data_lake
Expected Result: SQL query with proper p_event_time filter and CloudTrail table
Validation: Query includes time filter and targets correct table
```

**Test Scenario 14: Schema Discovery**

```
Prompt: "Show me the schema for AWS CloudTrail logs so I can write better queries"
Expected Tools: get_table_schema
Expected Result: Complete table schema with column names and types
Validation: Schema includes all expected CloudTrail fields
```

**Test Scenario 15: Database Structure**

```
Prompt: "List all available databases and tables in the data lake"
Expected Tools: list_databases, list_database_tables
Expected Result: Complete database and table listing
Validation: Shows panther_logs.public and other available databases
```

**Test Scenario 16: Alert Event Correlation**

```
Prompt: "Analyze events across alerts [ALERT_ID_1] and [ALERT_ID_2] to find common patterns"
Expected Tools: get_alert_event_stats
Expected Result: Time-grouped analysis showing common entities and patterns
Validation: Results show temporal patterns and shared indicators
```

### Sources and Configuration

#### Log Source Management

**Test Scenario 17: Source Health Check**

```
Prompt: "Show me all log sources and their health status"
Expected Tools: list_log_sources
Expected Result: Complete list of log sources with health indicators
Validation: Health status is clearly indicated for each source
```

**Test Scenario 18: HTTP Source Configuration**

```
Prompt: "Get detailed configuration for HTTP log source [SOURCE_ID]"
Expected Tools: get_http_log_source
Expected Result: Complete HTTP source configuration including auth settings
Validation: All configuration details are present and properly formatted
```

**Test Scenario 19: Schema Management**

```
Prompt: "List all available log type schemas for AWS services"
Expected Tools: list_log_type_schemas
Expected Result: Filtered list of AWS-related schemas
Validation: Contains filtering and shows relevant AWS log types
```

**Test Scenario 20: Detailed Schema Analysis**

```
Prompt: "Get detailed schema information for AWS.CloudTrail and AWS.VPCFlow"
Expected Tools: get_log_type_schema_details
Expected Result: Complete schema specifications for both log types
Validation: Full schema details with field mappings and transformations
```

### Metrics and Monitoring

#### Alert Metrics Analysis

**Test Scenario 21: Severity Distribution**

```
Prompt: "Show me alert counts by severity for the last week"
Expected Tools: get_severity_alert_metrics
Expected Result: Alert metrics grouped by severity with time range
Validation: Date range covers last week and includes all severity levels
Note: Use alert_types=["Rule", "Policy"] (not "ALERT") for proper validation
```

**Test Scenario 22: Rule Performance Analysis**

```
Prompt: "Identify the top 10 detection rules generating the most alerts this month"
Expected Tools: get_rule_alert_metrics
Expected Result: Rules ranked by alert count with proper date filtering
Validation: Time range covers current month and shows top alerting rules
```

**Test Scenario 23: Data Ingestion Monitoring**

```
Prompt: "Show me data ingestion volume by log type for today"
Expected Tools: get_bytes_processed_per_log_type_and_source
Expected Result: Bytes processed metrics broken down by log type and source
Validation: Current day data with proper breakdown
```

### User and Access Management

#### User Information Management

**Test Scenario 24: User Directory**

```
Prompt: "List all active users in the Panther instance"
Expected Tools: list_users
Expected Result: Complete user listing with basic information
Validation: Shows user emails, names, and status information
```

**Test Scenario 25: User Details**

```
Prompt: "Get detailed information about user [USER_EMAIL]"
Expected Tools: get_user
Expected Result: Complete user profile including roles and permissions
Validation: All user details properly displayed
```

**Test Scenario 26: Role Analysis**

```
Prompt: "Show me all available roles and their permissions"
Expected Tools: list_roles, get_role (for each role)
Expected Result: Complete role listing with detailed permissions
Validation: All roles shown with comprehensive permission details
```

### Global Helpers and Data Models

#### Code Management Tools

**Test Scenario 27: Helper Function Discovery**

```
Prompt: "List all global helper functions related to AWS"
Expected Tools: list_global_helpers
Expected Result: AWS-related helper functions with descriptions
Validation: Proper filtering and relevant results
```

**Test Scenario 28: Helper Code Analysis**

```
Prompt: "Get the complete code for global helper [HELPER_ID]"
Expected Tools: get_global_helper
Expected Result: Complete Python code and documentation for the helper
Validation: Full code with proper formatting and documentation
```

**Test Scenario 29: Data Model Management**

```
Prompt: "Show me all available data models and get details for the user data model"
Expected Tools: list_data_models, get_data_model
Expected Result: Data model listing and detailed UDM mappings
Validation: Complete data model information with field mappings
```

### Scheduled Queries

#### Query Management

**Test Scenario 30: Scheduled Query Discovery**

```
Prompt: "List all scheduled queries and show me details for any security-related ones"
Expected Tools: list_scheduled_queries, get_scheduled_query
Expected Result: Query listings and detailed SQL for security queries
Validation: Schedule information and complete SQL provided
```

## Integration Testing Scenarios

### Cross-Tool Workflows

**Test Scenario 31: Alert Investigation Workflow**

```
Prompt: "I need to investigate a suspicious login alert. First show me recent authentication-related alerts, then get details on the highest priority one, analyze its events, and check if we have any related detection rules."

Expected Tools: list_alerts → get_alert → get_alert_events → list_detections
Expected Flow:
1. List alerts filtered for authentication activity
2. Get detailed info on selected alert
3. Analyze events in the alert
4. Find related detection rules

Validation: Seamless workflow with contextual tool selection
```

**Test Scenario 32: Rule Performance Analysis Workflow**

```
Prompt: "Help me analyze rule performance issues. Show me which rules are generating the most alerts this week, get details on the top alerting rule, and check if we can optimize it by looking at recent alerts it generated."

Expected Tools: get_rule_alert_metrics → get_detection → list_alerts → get_alert_events
Expected Flow:
1. Get metrics to identify top alerting rules
2. Examine rule code and configuration
3. Look at recent alerts from that rule
4. Analyze sample events to understand patterns

Validation: Data-driven analysis with proper tool chaining
```

**Test Scenario 33: Data Pipeline Health Check**

```
Prompt: "Perform a complete health check of our data pipeline. Check log source status, look for any system errors, analyze ingestion volumes, and identify any classification issues."

Expected Tools: list_log_sources → list_alerts (system errors) → get_bytes_processed_per_log_type_and_source → query_data_lake (classification failures)
Expected Flow:
1. Check all log source health
2. Look for system error alerts
3. Review ingestion volume metrics
4. Query for classification failures

Validation: Comprehensive pipeline analysis
```

## Error Handling Validation

### Input Validation Testing

**Test Scenario 34: Invalid Parameters**

```
Test each tool category with invalid parameters:
- Invalid date formats in metrics tools
- Invalid severity levels in alert filtering
- Invalid rule IDs in rule metrics
- Invalid SQL in data lake queries
- Invalid UUIDs in scheduled query lookups

Expected Result: Clear error messages with specific validation feedback
Validation: Errors are informative and help correct the input
```

**Test Scenario 35: Permission Boundary Testing**

```
Test operations that require elevated permissions:
- Attempt to disable detections
- Try to update alert assignees
- Attempt to cancel data lake queries

Expected Result: Clear permission denied messages when appropriate
Validation: Error messages indicate required permissions
```

**Test Scenario 36: Resource Not Found Handling**

```
Test with non-existent resources:
- Get alert with invalid ID
- Get detection rule that doesn't exist
- Query for user that doesn't exist

Expected Result: Appropriate "not found" responses
Validation: Clear messaging about resource availability
```

## Performance Testing

### Response Time Validation

**Test Scenario 37: Large Query Handling**

```
Prompt: "Query the last 7 days of AWS CloudTrail logs and count events by user"
Expected Tools: query_data_lake
Expected Result: Query completes within reasonable time or provides timeout feedback
Validation: Performance is acceptable or timeout is handled gracefully
```

**Test Scenario 38: Bulk Operations**

```
Prompt: "Get alert metrics for the last 30 days with 15-minute intervals"
Expected Tools: get_rule_alert_metrics or get_severity_alert_metrics
Expected Result: Large dataset handled efficiently
Validation: Response time is reasonable for data volume
```

**Test Scenario 39: Pagination Testing**

```
Prompt: "List all detection rules in the system, handling pagination as needed"
Expected Tools: list_detections (multiple calls with cursor)
Expected Result: All rules retrieved through proper pagination
Validation: Pagination works correctly for large result sets
```

## Release Validation Checklist

### Pre-Release Verification

Before marking a release as validated, verify:

#### Core Functionality

- [ ] All 40+ tools are discoverable and callable
- [ ] Authentication and permissions work correctly  
- [ ] Basic CRUD operations function for all resource types
- [ ] Error handling provides clear, actionable feedback

#### Data Integrity

- [ ] Date parameter handling works consistently
- [ ] Parameter validation prevents invalid inputs
- [ ] SQL queries include required time filters
- [ ] Pagination works correctly for large datasets

#### Performance

- [ ] Response times are acceptable for typical operations
- [ ] Large queries handle timeouts gracefully
- [ ] Bulk operations complete successfully

#### Integration

- [ ] Cross-tool workflows execute smoothly
- [ ] Context is maintained across multi-tool operations
- [ ] Complex analysis scenarios complete successfully

#### Error Scenarios

- [ ] Invalid parameters generate helpful error messages
- [ ] Permission boundaries are enforced correctly
- [ ] Network and service errors are handled gracefully
- [ ] Resource not found scenarios provide clear feedback

### Post-Validation Report

After completing all test scenarios, provide a summary including:

1. **Test Coverage**: Number of tools tested and scenarios completed
2. **Issues Found**: Any bugs, performance problems, or usability issues
3. **Recommendations**: Suggestions for improvements or optimizations
4. **Risk Assessment**: Evaluation of release readiness

### Test Data Requirements

For effective testing, ensure access to:

- Recent alerts (last 7 days) across different severities
- Multiple detection types (rules, policies, scheduled rules)
- Various log sources with different health states
- Historical data spanning several months for metrics testing
- User accounts with different permission levels
- Sample global helpers and data models

## Notes for AI Agents

When executing these tests:

1. **Be Systematic**: Follow test scenarios in order, building complexity gradually
2. **Validate Outputs**: Check that tool responses match expected formats and contain required data
3. **Note Anomalies**: Report any unexpected behavior, error messages, or performance issues
4. **Use Real Data**: Test with actual data from the Panther instance when possible
5. **Document Findings**: Keep track of what works well and what needs improvement
6. **Test Edge Cases**: Don't just test happy paths - try boundary conditions and error scenarios

This testing guide ensures comprehensive validation of MCP Panther functionality before releases, helping maintain high quality and reliability for end users.
