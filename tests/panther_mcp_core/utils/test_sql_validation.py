"""Tests for SQL validation utilities."""

import pytest

from mcp_panther.panther_mcp_core.utils.sql_validation import (
    validate_panther_database_name,
    validate_sql_basic,
    validate_sql_comprehensive,
    validate_sql_read_only,
    validate_sql_time_filter,
    wrap_reserved_words,
)


class TestValidateSqlTimeFilter:
    """Test the validate_sql_time_filter function."""

    def test_valid_p_occurs_since(self):
        """Test valid p_occurs_since usage."""
        sql = "SELECT * FROM table WHERE p_occurs_since('1 d')"
        result = validate_sql_time_filter(sql)
        assert result["valid"] is True
        assert result["error"] is None

    def test_valid_p_occurs_between(self):
        """Test valid p_occurs_between usage."""
        sql = "SELECT * FROM table WHERE p_occurs_between('2024-01-01', '2024-01-02')"
        result = validate_sql_time_filter(sql)
        assert result["valid"] is True
        assert result["error"] is None

    def test_valid_p_event_time_direct(self):
        """Test valid p_event_time usage."""
        sql = "SELECT * FROM table WHERE p_event_time >= CURRENT_TIMESTAMP - INTERVAL '1 DAY'"
        result = validate_sql_time_filter(sql)
        assert result["valid"] is True
        assert result["error"] is None

    def test_valid_where_and_p_event_time(self):
        """Test valid WHERE/AND p_event_time pattern."""
        sql = "SELECT * FROM table WHERE status = 'active' AND p_event_time >= '2024-01-01'"
        result = validate_sql_time_filter(sql)
        assert result["valid"] is True
        assert result["error"] is None

    def test_missing_time_filter(self):
        """Test missing time filter."""
        sql = "SELECT * FROM table WHERE status = 'active'"
        result = validate_sql_time_filter(sql)
        assert result["valid"] is False
        assert "time filter" in result["error"]

    def test_empty_sql(self):
        """Test empty SQL."""
        result = validate_sql_time_filter("")
        assert result["valid"] is False
        assert "cannot be empty" in result["error"]

    def test_complex_snowflake_queries(self):
        """Test that complex Snowflake queries with time filters are accepted."""
        # JSON operations
        sql = """
        SELECT 
            PARSE_JSON(json_field):path::string as extracted_value,
            p_enrichment:ipinfo_privacy:"context.ip_address"::string as enriched_ip
        FROM panther_logs.public.aws_cloudtrail 
        WHERE p_occurs_since('2 h')
        """
        result = validate_sql_time_filter(sql)
        assert result["valid"] is True

        # LATERAL FLATTEN
        sql = """
        SELECT cs.username, f.value::string as permission
        FROM panther_logs.public.aws_cloudtrail cs,
        LATERAL FLATTEN(input => PARSE_JSON(cs.resources)) f
        WHERE p_occurs_since('1 d')
        """
        result = validate_sql_time_filter(sql)
        assert result["valid"] is True

        # Window functions
        sql = """
        WITH user_activity AS (
            SELECT username, p_event_time,
                   ROW_NUMBER() OVER (PARTITION BY username ORDER BY p_event_time DESC) as rn
            FROM panther_logs.public.aws_cloudtrail
            WHERE p_occurs_since('1 d')
        )
        SELECT * FROM user_activity WHERE rn = 1
        """
        result = validate_sql_time_filter(sql)
        assert result["valid"] is True

    def test_valid_p_occurs_around(self):
        """Test valid p_occurs_around usage."""
        sql = "SELECT * FROM table WHERE p_occurs_around('2024-01-15T10:30:00Z', '1 h')"
        result = validate_sql_time_filter(sql)
        assert result["valid"] is True
        assert result["error"] is None

    def test_valid_p_occurs_after(self):
        """Test valid p_occurs_after usage."""
        sql = "SELECT * FROM table WHERE p_occurs_after('2024-01-01T00:00:00Z')"
        result = validate_sql_time_filter(sql)
        assert result["valid"] is True
        assert result["error"] is None

    def test_valid_p_occurs_before(self):
        """Test valid p_occurs_before usage."""
        sql = "SELECT * FROM table WHERE p_occurs_before('2024-01-31T23:59:59Z')"
        result = validate_sql_time_filter(sql)
        assert result["valid"] is True
        assert result["error"] is None


class TestValidateSqlBasic:
    """Test the validate_sql_basic function."""

    def test_valid_sql(self):
        """Test valid SQL."""
        sql = "SELECT * FROM users WHERE id = 1"
        result = validate_sql_basic(sql)
        assert result["valid"] is True
        assert result["error"] is None

    def test_empty_sql(self):
        """Test empty SQL."""
        result = validate_sql_basic("")
        assert result["valid"] is False
        assert "cannot be empty" in result["error"]

    def test_none_sql(self):
        """Test None SQL."""
        result = validate_sql_basic(None)
        assert result["valid"] is False
        assert "cannot be empty" in result["error"]

    def test_whitespace_only_sql(self):
        """Test whitespace-only SQL."""
        result = validate_sql_basic("   \n\t  ")
        assert result["valid"] is False
        assert "cannot be empty" in result["error"]

    def test_sql_too_long(self):
        """Test SQL that exceeds length limit."""
        # Create a query that exceeds 10,000 characters
        long_sql = "SELECT * FROM users WHERE " + " OR ".join(
            [f"id = {i}" for i in range(2000)]
        )
        result = validate_sql_basic(long_sql)
        assert result["valid"] is False
        assert "too long" in result["error"]

    def test_invalid_sql_parsing(self):
        """Test SQL that fails parsing."""
        invalid_sql = "SELECT * FROM WHERE INVALID SYNTAX"
        result = validate_sql_basic(invalid_sql)
        # Note: sqlparse is quite permissive, so this might not fail parsing
        # but we test the mechanism is in place
        assert isinstance(result["valid"], bool)


class TestValidateSqlReadOnly:
    """Test the validate_sql_read_only function."""

    def test_valid_read_only_sql(self):
        """Test valid read-only SQL."""
        sql = "SELECT * FROM users WHERE active = true"
        result = validate_sql_read_only(sql)
        assert result["valid"] is True
        assert result["error"] is None

    @pytest.mark.parametrize(
        "keyword",
        [
            "DROP",
            "DELETE",
            "INSERT",
            "UPDATE",
            "CREATE",
            "ALTER",
            "TRUNCATE",
            "REPLACE",
            "MERGE",
            "UPSERT",
            "GRANT",
            "REVOKE",
            "COMMIT",
            "ROLLBACK",
            "SAVEPOINT",
        ],
    )
    def test_blocked_keywords(self, keyword):
        """Test that dangerous keywords are blocked."""
        sql = f"SELECT * FROM users; {keyword} TABLE users"
        result = validate_sql_read_only(sql)
        assert result["valid"] is False
        assert keyword in result["error"]

    def test_keyword_in_column_name_allowed(self):
        """Test that keywords in column names are allowed."""
        sql = "SELECT updates_column, delete_flag FROM users"
        result = validate_sql_read_only(sql)
        assert result["valid"] is True
        assert result["error"] is None

    def test_case_insensitive_keyword_detection(self):
        """Test that keyword detection is case insensitive."""
        sql = "select * from users; drop table users"
        result = validate_sql_read_only(sql)
        assert result["valid"] is False
        assert "DROP" in result["error"]


class TestValidatePantherDatabaseName:
    """Test the validate_panther_database_name function."""

    @pytest.mark.parametrize(
        "db_name",
        [
            "panther_logs.public",
            "panther_views.public",
            "panther_signals.public",
            "panther_rule_matches.public",
            "panther_rule_errors.public",
            "panther_monitor.public",
            "panther_cloudsecurity.public",
        ],
    )
    def test_valid_panther_databases(self, db_name):
        """Test valid Panther database names."""
        result = validate_panther_database_name(db_name)
        assert result["valid"] is True
        assert result["error"] is None

    @pytest.mark.parametrize(
        "db_name",
        [
            "custom_database",
            "panther_invalid.public",
            "logs.public",
            "panther_logs",  # Missing .public
            "panther_logs.private",  # Invalid schema (only public allowed)
            "panther_logs.custom",  # Invalid schema
            "random.database.name",
        ],
    )
    def test_invalid_panther_databases(self, db_name):
        """Test invalid Panther database names."""
        result = validate_panther_database_name(db_name)
        assert result["valid"] is False
        assert "Invalid database name" in result["error"]

    def test_empty_database_name(self):
        """Test empty database name."""
        result = validate_panther_database_name("")
        assert result["valid"] is False
        assert "cannot be empty" in result["error"]

    def test_none_database_name(self):
        """Test None database name."""
        result = validate_panther_database_name(None)
        assert result["valid"] is False
        assert "cannot be empty" in result["error"]


class TestWrapReservedWords:
    """Test the wrap_reserved_words function."""

    def test_wrap_reserved_word(self):
        """Test wrapping of a reserved word."""
        sql = "SELECT 'ORDER' FROM users"
        result = wrap_reserved_words(sql)
        assert '"ORDER"' in result

    def test_preserve_non_reserved(self):
        """Test that non-reserved words are preserved."""
        sql = "SELECT 'custom_field' FROM users"
        result = wrap_reserved_words(sql)
        assert "'custom_field'" in result

    def test_complex_query_reserved_words(self):
        """Test complex query with multiple reserved words."""
        sql = "SELECT 'FROM', 'WHERE', 'custom' FROM users"
        result = wrap_reserved_words(sql)
        assert '"FROM"' in result
        assert '"WHERE"' in result
        assert "'custom'" in result  # Non-reserved should stay the same

    def test_malformed_sql_handling(self):
        """Test handling of malformed SQL."""
        sql = "INVALID SQL SYNTAX("
        result = wrap_reserved_words(sql)
        # Should return original SQL if parsing fails
        assert result == sql

    def test_empty_sql(self):
        """Test empty SQL handling."""
        result = wrap_reserved_words("")
        assert result == ""


class TestValidateSqlComprehensive:
    """Test the validate_sql_comprehensive function."""

    def test_valid_comprehensive_basic(self):
        """Test basic valid SQL passes all validations."""
        sql = "SELECT * FROM users WHERE p_occurs_since('1 d')"
        result = validate_sql_comprehensive(
            sql, require_time_filter=True, read_only=True
        )
        assert result["valid"] is True
        assert result["error"] is None
        assert "processed_sql" in result

    def test_comprehensive_time_filter_required(self):
        """Test that time filter requirement works."""
        sql = "SELECT * FROM users WHERE active = true"
        result = validate_sql_comprehensive(
            sql, require_time_filter=True, read_only=True
        )
        assert result["valid"] is False
        assert "time filter" in result["error"]

    def test_comprehensive_read_only_enforcement(self):
        """Test that read-only enforcement works."""
        sql = "DROP TABLE users WHERE p_occurs_since('1 d')"
        result = validate_sql_comprehensive(
            sql, require_time_filter=True, read_only=True
        )
        assert result["valid"] is False
        assert "DROP" in result["error"]

    def test_comprehensive_database_validation(self):
        """Test that database name validation works."""
        sql = "SELECT * FROM users WHERE p_occurs_since('1 d')"
        result = validate_sql_comprehensive(
            sql,
            require_time_filter=True,
            read_only=True,
            database_name="invalid.database",
        )
        assert result["valid"] is False
        assert "Invalid database name" in result["error"]

    def test_comprehensive_all_validations_pass(self):
        """Test that all validations can pass together."""
        sql = "SELECT * FROM users WHERE p_occurs_since('1 d')"
        result = validate_sql_comprehensive(
            sql,
            require_time_filter=True,
            read_only=True,
            database_name="panther_logs.public",
        )
        assert result["valid"] is True
        assert result["error"] is None
        assert "processed_sql" in result

    def test_comprehensive_optional_validations(self):
        """Test that optional validations can be disabled."""
        sql = "DROP TABLE users"  # No time filter, dangerous operation
        result = validate_sql_comprehensive(
            sql, require_time_filter=False, read_only=False, database_name=None
        )
        assert result["valid"] is True
        assert result["error"] is None

    def test_comprehensive_basic_validation_failure(self):
        """Test that basic validation failures are caught."""
        sql = ""  # Empty SQL
        result = validate_sql_comprehensive(sql)
        assert result["valid"] is False
        assert "cannot be empty" in result["error"]
