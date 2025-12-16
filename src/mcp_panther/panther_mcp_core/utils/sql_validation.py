"""
Shared utilities for SQL validation in Panther MCP tools.
"""

import logging
import re
from typing import Any

import sqlparse

logger = logging.getLogger("mcp-panther")

# Snowflake reserved words that should be quoted when used as identifiers
SNOWFLAKE_RESERVED_WORDS = {
    "SELECT",
    "FROM",
    "WHERE",
    "JOIN",
    "LEFT",
    "RIGHT",
    "INNER",
    "OUTER",
    "ON",
    "AS",
    "ORDER",
    "GROUP",
    "BY",
    "HAVING",
    "UNION",
    "ALL",
    "DISTINCT",
    "INSERT",
    "UPDATE",
    "DELETE",
    "CREATE",
    "ALTER",
    "DROP",
    "TABLE",
    "VIEW",
    "INDEX",
    "COLUMN",
    "PRIMARY",
    "KEY",
    "FOREIGN",
    "UNIQUE",
    "NOT",
    "NULL",
    "DEFAULT",
    "CHECK",
    "CONSTRAINT",
    "REFERENCES",
    "CASCADE",
    "RESTRICT",
    "SET",
    "VALUES",
    "INTO",
    "CASE",
    "WHEN",
    "THEN",
    "ELSE",
    "END",
    "IF",
    "EXISTS",
    "LIKE",
    "BETWEEN",
    "IN",
    "IS",
    "AND",
    "OR",
    "WITH",
}


def validate_sql_basic(sql: str) -> dict[str, Any]:
    """
    Validate basic SQL structure and safety.

    Args:
        sql: SQL query string to validate

    Returns:
        Dict with validation results:
        - valid: Boolean indicating if validation passed
        - error: Error message if validation failed
    """
    if not sql or not sql.strip():
        return {"valid": False, "error": "SQL query cannot be empty"}

    # Check length limits (prevent context overflow)
    if len(sql) > 10000:  # 10KB limit
        return {
            "valid": False,
            "error": "Query too long. Maximum 10,000 characters allowed",
        }

    # Basic SQL parsing validation
    try:
        parsed = sqlparse.parse(sql.strip())
        if not parsed:
            return {"valid": False, "error": "Invalid SQL query"}
    except Exception:
        return {"valid": False, "error": "Failed to parse SQL query"}

    return {"valid": True, "error": None}


def validate_sql_time_filter(sql: str) -> dict[str, Any]:
    """
    Validate that SQL query contains required time filter or macro.

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

    # Check for Panther time macros (these are always valid)
    has_occurs_since = "p_occurs_since" in sql_lower
    has_occurs_between = "p_occurs_between" in sql_lower
    has_occurs_around = "p_occurs_around" in sql_lower
    has_occurs_after = "p_occurs_after" in sql_lower
    has_occurs_before = "p_occurs_before" in sql_lower

    # Check for proper WHERE/AND + p_event_time pattern (more strict)
    where_pattern = re.search(
        r"\b(where|and)\s+.*?(?:[\w.]+\.)?p_event_time\s*(>=|<=|=|>|<|between)",
        sql_lower,
        re.IGNORECASE | re.DOTALL,
    )

    if not (
        has_occurs_since
        or has_occurs_between
        or has_occurs_around
        or has_occurs_after
        or has_occurs_before
        or where_pattern
    ):
        return {
            "valid": False,
            "error": "Query must include a time filter: either `p_event_time` condition or Panther macro",
        }

    return {"valid": True, "error": None}


def validate_panther_database_name(database_name: str) -> dict[str, Any]:
    """
    Validate Panther database name format.

    Args:
        database_name: Database name to validate

    Returns:
        Dict with validation results:
        - valid: Boolean indicating if validation passed
        - error: Error message if validation failed
    """
    if not database_name or not database_name.strip():
        return {"valid": False, "error": "Database name cannot be empty"}

    # Valid Panther database patterns (only public schema)
    valid_patterns = [
        r"^panther_logs\.public$",
        r"^panther_views\.public$",
        r"^panther_signals\.public$",
        r"^panther_rule_matches\.public$",
        r"^panther_rule_errors\.public$",
        r"^panther_monitor\.public$",
        r"^panther_cloudsecurity\.public$",
    ]

    database_lower = database_name.lower().strip()

    for pattern in valid_patterns:
        if re.match(pattern, database_lower):
            return {"valid": True, "error": None}

    return {
        "valid": False,
        "error": f"Invalid database name '{database_name}'. Must be a valid Panther database (e.g., 'panther_logs.public')",
    }


def wrap_reserved_words(sql: str) -> str:
    """
    Wrap reserved words in SQL using sqlparse.

    This function:
    1. Parses the SQL using sqlparse
    2. Identifies string literals that match reserved words
    3. Converts single-quoted reserved words to double-quoted ones

    Args:
        sql: The SQL query string to process

    Returns:
        The SQL with reserved words properly quoted
    """
    try:
        # Parse the SQL
        parsed = sqlparse.parse(sql)[0]

        # Convert the parsed SQL back to string, but process tokens
        result = []
        for token in parsed.flatten():
            if token.ttype is sqlparse.tokens.Literal.String.Single:
                # Remove quotes and check if it's a reserved word
                value = token.value.strip("'")
                if value.upper() in SNOWFLAKE_RESERVED_WORDS:
                    # Convert to double-quoted identifier
                    result.append(f'"{value}"')
                else:
                    result.append(token.value)
            else:
                result.append(token.value)

        return "".join(result)
    except Exception as e:
        logger.warning(f"Failed to parse SQL for reserved words: {e}")
        return sql


def validate_sql_comprehensive(
    sql: str,
    require_time_filter: bool = False,
    database_name: str | None = None,
) -> dict[str, Any]:
    """
    Comprehensive SQL validation for Panther queries.

    Args:
        sql: SQL query string to validate
        require_time_filter: Whether to require p_event_time filter
        database_name: Database name to validate (optional)

    Returns:
        Dict with validation results:
        - valid: Boolean indicating if all validations passed
        - error: Error message if any validation failed
        - processed_sql: SQL with reserved words processed (if valid)
    """
    # Basic validation
    basic_result = validate_sql_basic(sql)
    if not basic_result["valid"]:
        return basic_result

    # Time filter validation
    if require_time_filter:
        time_result = validate_sql_time_filter(sql)
        if not time_result["valid"]:
            return time_result

    # Database name validation
    if database_name:
        db_result = validate_panther_database_name(database_name)
        if not db_result["valid"]:
            return db_result

    # Process reserved words
    processed_sql = wrap_reserved_words(sql)

    return {
        "valid": True,
        "error": None,
        "processed_sql": processed_sql,
    }
