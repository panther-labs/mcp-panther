# MCP Panther v2.1.0-rc1

## 🚨 Breaking Changes

- **Data Lake Tools**: `summarize_alert_events` has been renamed to `get_alert_event_stats` to better reflect its statistical aggregation functionality and avoid confusion with the new AI-powered analysis tools

- **Default Filters Removed**: `list_alerts` and `list_detections` now return all items by default instead of applying filters to improve discoverability:
  - `list_alerts`: No longer filters by severity, status, or subtypes by default (previously filtered to `["CRITICAL", "HIGH", "MEDIUM", "LOW"]` severities and `["OPEN", "TRIAGED", "RESOLVED", "CLOSED"]` statuses)
  - `list_detections`: No longer filters by state or severity by default (previously filtered to `"enabled"` state and `["MEDIUM", "HIGH", "CRITICAL"]` severities)

## Tools

### 🆕 New Tools

- **Alert Management**:
  - `bulk_update_alerts` - Efficiently update multiple alerts at once with status, assignee, and/or comment changes. Supports up to 25 alerts per call with atomic operations.

- **AI-Powered Analysis**:
  - `start_ai_alert_triage` - Start an AI-powered triage analysis for a Panther alert with intelligent insights, risk assessment, and recommendations
  - `get_ai_alert_triage_summary` - Retrieve the latest AI triage summary previously generated for a specific alert

### 🔄 Changed Tools

- **Data Lake**: `summarize_alert_events` → `get_alert_event_stats`
  - Renamed to clarify this tool performs statistical aggregation of alert events (grouping entities, counting occurrences, temporal analysis)
  - Functionality remains the same: analyzes patterns and relationships across multiple alerts by aggregating their event data into time-based groups

## Functionality

### 🆕 New Features

- **AI-Powered Alert Triage**: Utilize Panther's embedded AI agents to analyze alerts and provide intelligent triage summaries including:
  - Risk assessment and severity context
  - Analysis of related events and entities
  - Recommended investigation steps
  - Potential impact and next actions

- **Bulk Alert Operations**: New `bulk_update_alerts` tool enables efficient mass management of alerts:
  - Update status, assignee, and comments in a single operation
  - Process up to 25 alerts per call
  - Detailed success/failure reporting per operation

- **Context Window Protection for Data Lake Queries**: `query_data_lake` now includes built-in protection against overwhelming AI context windows:
  - New `max_rows` parameter (default: 100, max: 999) limits result set size
  - Cursor-based pagination support for retrieving large result sets incrementally
  - Automatic truncation warnings when results exceed limits
  - Prevents token overflow while maintaining access to complete datasets through pagination

### 🔧 Improvements

- **Alert Management**:
  - `list_alerts` default timeframe expanded from "today" to "last 7 days" for better alert visibility and discovery
  - Improves user experience by showing recent alerts without requiring explicit date parameters

- **Documentation**:
  - Added comprehensive test scenarios for all new tools in release testing guide
  - Updated README.md with all new tools and sample prompts
  - Added parameter clarification for `get_severity_alert_metrics` (use `alert_types=["Rule", "Policy"]`)

- **Bug Fixes**:
  - Fixed page size parameter in `get_alert_event_stats` (formerly `summarize_alert_events`) to respect API's 1000-row limit

### 🐛 Bug Fixes

- **`get_alert_event_stats`**: Fixed PageSize validation error that occurred when aggregating events across multiple alerts

## Contributors

Special thanks to all contributors who made this release possible:

- **Jack Naglieri** - Core development, AI triage integration, bulk operations
- **Bianca Fu** - Testing, validation, documentation updates

---

## Migration Guide

### For users upgrading from v2.0

1. **Update tool calls**: If you're using `summarize_alert_events`, update to the new name:

   ```python
   # Old approach (v2.0)
   result = await client.call_tool("summarize_alert_events", {
       "alert_ids": ["alert-1", "alert-2"],
       "time_window": 30
   })

   # New approach (v2.1)
   result = await client.call_tool("get_alert_event_stats", {
       "alert_ids": ["alert-1", "alert-2"],
       "time_window": 30
   })
   ```

2. **Adjust filter expectations**: `list_alerts` and `list_detections` now require explicit filters if you want filtered results:

   ```python
   # Old behavior (v2.0) - automatically filtered
   result = await client.call_tool("list_alerts", {})
   # Returned only CRITICAL/HIGH/MEDIUM/LOW alerts with OPEN/TRIAGED/RESOLVED/CLOSED status from TODAY

   # New behavior (v2.1) - returns all alerts from LAST 7 DAYS unless explicitly filtered
   result = await client.call_tool("list_alerts", {})
   # Returns all alerts from last 7 days with all severities and statuses

   # To replicate v2.0 behavior with explicit filters:
   result = await client.call_tool("list_alerts", {
       "start_date": "2025-10-01T00:00:00Z",  # Today
       "end_date": "2025-10-01T23:59:59Z",
       "severities": ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
       "statuses": ["OPEN", "TRIAGED", "RESOLVED", "CLOSED"]
   })
   ```

   **Note**: The default timeframe has expanded from "today" to "last 7 days" for better alert discovery.

3. **Use pagination for large data lake queries**: Take advantage of new context window protection:

   ```python
   # Retrieve large result sets with pagination
   result = await client.call_tool("query_data_lake", {
       "sql": "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_occurs_since('1 d')",
       "max_rows": 100  # Default: 100, max: 999
   })

   # If more results available, use cursor for next page
   if result["has_next_page"]:
       next_result = await client.call_tool("query_data_lake", {
           "sql": "SELECT * FROM panther_logs.public.aws_cloudtrail WHERE p_occurs_since('1 d')",
           "cursor": result["next_cursor"]
       })
   ```

4. **Try the new AI features**: Explore the new AI-powered alert triage capabilities:

   ```python
   # Start AI triage analysis
   triage_result = await client.call_tool("start_ai_alert_triage", {
       "alert_id": "your-alert-id",
       "output_length": "medium"
   })

   # Retrieve previously generated triage summary
   summary = await client.call_tool("get_ai_alert_triage_summary", {
       "alert_id": "your-alert-id"
   })
   ```

5. **Leverage bulk operations**: Use `bulk_update_alerts` for efficient mass alert management:

   ```python
   # Update multiple alerts at once
   result = await client.call_tool("bulk_update_alerts", {
       "alert_ids": ["alert-1", "alert-2", "alert-3"],
       "status": "RESOLVED",
       "comment": "Investigated and resolved - false positive"
   })
   ```
