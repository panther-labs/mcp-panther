"""
Shared utilities for SQL validation in Panther MCP tools.
"""

import re
from typing import Any, Dict


def validate_sql_time_filter(sql: str) -> Dict[str, Any]:
    """
    Validate that SQL query contains required p_event_time filter.

    Args:
        sql: SQL query string to validate

    Returns:
        Dict with validation results:
        - valid: Boolean indicating if validation passed
        - error: Error message if validation failed
    """
    if not sql or not sql.strip():
        return {"valid": False, "error": "SQL query cannot be empty"}

    sql_lower = sql.lower()

    # Check for p_event_time filter using various patterns
    has_p_event_time = "p_event_time" in sql_lower
    has_occurs_since = "p_occurs_since" in sql_lower
    has_occurs_between = "p_occurs_between" in sql_lower

    # Also check for WHERE/AND + p_event_time pattern from data_lake.py
    where_pattern = re.search(
        r"\b(where|and)\s+.*?(?:[\w.]+\.)?p_event_time\s*(>=|<=|=|>|<|between)",
        sql_lower,
        re.IGNORECASE | re.DOTALL,
    )

    if not (
        has_p_event_time or has_occurs_since or has_occurs_between or where_pattern
    ):
        return {
            "valid": False,
            "error": "Query must include a p_event_time filter (e.g., p_occurs_since('1 d'), p_occurs_between(...), or WHERE p_event_time >= ...) for performance",
        }

    return {"valid": True, "error": None}
