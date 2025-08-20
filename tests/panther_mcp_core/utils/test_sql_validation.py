"""Tests for SQL validation utilities."""

from mcp_panther.panther_mcp_core.utils.sql_validation import validate_sql_time_filter


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
        assert "p_event_time filter" in result["error"]

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
