from mcp_panther.panther_mcp_core.permissions import (
    Permission,
    all_perms,
    any_perms,
    convert_permissions,
    perms,
)


def test_permission_enum():
    """Test that Permission enum values are correctly defined."""
    assert Permission.ALERT_READ.value == "Read Alerts"
    assert Permission.ALERT_MODIFY.value == "Manage Alerts"
    assert Permission.DATA_ANALYTICS_READ.value == "Query Data Lake"
    assert Permission.LOG_SOURCE_READ.value == "View Log Sources"
    assert Permission.SUMMARY_READ.value == "Read Panther Metrics"
    assert Permission.ORGANIZATION_API_TOKEN_READ.value == "Read API Token Info"
    assert Permission.POLICY_READ.value == "View Policies"
    assert Permission.POLICY_MODIFY.value == "Manage Policies"
    assert Permission.RULE_MODIFY.value == "Manage Rules"
    assert Permission.RULE_READ.value == "View Rules"
    assert Permission.USER_READ.value == "Read User Info"
    assert Permission.USER_MODIFY.value == "Manage Users"


def test_convert_permissions():
    """Test converting raw permission strings to Permission enums."""
    raw_perms = ["RuleRead", "PolicyRead", "InvalidPerm"]
    converted = convert_permissions(raw_perms)
    assert len(converted) == 2
    assert Permission.RULE_READ in converted
    assert Permission.POLICY_READ in converted


def test_perms():
    """Test the perms function for creating permission specifications."""
    # Test with any_of
    result = perms(any_of=[Permission.ALERT_READ, Permission.ALERT_MODIFY])
    assert "any_of" in result
    assert len(result["any_of"]) == 2
    assert "Read Alerts" in result["any_of"]
    assert "Manage Alerts" in result["any_of"]

    # Test with all_of
    result = perms(all_of=[Permission.ALERT_READ, Permission.ALERT_MODIFY])
    assert "all_of" in result
    assert len(result["all_of"]) == 2
    assert "Read Alerts" in result["all_of"]
    assert "Manage Alerts" in result["all_of"]

    # Test with both
    result = perms(any_of=[Permission.ALERT_READ], all_of=[Permission.ALERT_MODIFY])
    assert "any_of" in result
    assert "all_of" in result
    assert len(result["any_of"]) == 1
    assert len(result["all_of"]) == 1

    # Test with string values
    result = perms(any_of=["Read Alerts", "Manage Alerts"])
    assert "any_of" in result
    assert len(result["any_of"]) == 2
    assert "Read Alerts" in result["any_of"]
    assert "Manage Alerts" in result["any_of"]


def test_any_perms():
    """Test the any_perms function for creating 'any of' permission specifications."""
    result = any_perms(Permission.ALERT_READ, Permission.ALERT_MODIFY)
    assert "any_of" in result
    assert len(result["any_of"]) == 2
    assert "Read Alerts" in result["any_of"]
    assert "Manage Alerts" in result["any_of"]

    # Test with string values
    result = any_perms("Read Alerts", "Manage Alerts")
    assert "any_of" in result
    assert len(result["any_of"]) == 2
    assert "Read Alerts" in result["any_of"]
    assert "Manage Alerts" in result["any_of"]


def test_all_perms():
    """Test the all_perms function for creating 'all of' permission specifications."""
    result = all_perms(Permission.ALERT_READ, Permission.ALERT_MODIFY)
    assert "all_of" in result
    assert len(result["all_of"]) == 2
    assert "Read Alerts" in result["all_of"]
    assert "Manage Alerts" in result["all_of"]

    # Test with string values
    result = all_perms("Read Alerts", "Manage Alerts")
    assert "all_of" in result
    assert len(result["all_of"]) == 2
    assert "Read Alerts" in result["all_of"]
    assert "Manage Alerts" in result["all_of"]
