import pytest
from mcp_panther.panther_mcp_core.permissions import (
    Permission,
    convert_permissions,
    perms,
    any_perms,
    all_perms,
    PermissionBuilder,
    requires_permissions,
)


def test_permission_enum_values():
    """Test that Permission enum values are correctly defined"""
    assert Permission.RULE_READ.value == "View Rules"
    assert Permission.RULE_MODIFY.value == "Manage Rules"
    assert Permission.POLICY_READ.value == "View Policies"
    assert Permission.USER_READ.value == "View Users"
    assert Permission.DATA_ANALYTICS_READ.value == "Query Data Lake"
    assert Permission.ALERT_READ.value == "View Alerts"
    assert Permission.ALERT_MODIFY.value == "Manage Alerts"
    assert Permission.SUMMARY_READ.value == "View Overview"
    assert Permission.LOG_SOURCE_READ.value == "View Log Sources"
    assert Permission.ORGANIZATION_API_TOKEN_READ.value == "Read API Token Info"


def test_convert_permissions():
    """Test permission conversion from raw strings to enum values"""
    # Test valid permissions
    raw_perms = ["RuleRead", "PolicyRead", "UserRead"]
    converted = convert_permissions(raw_perms)
    assert len(converted) == 3
    assert Permission.RULE_READ in converted
    assert Permission.POLICY_READ in converted
    assert Permission.USER_READ in converted

    # Test with invalid permissions
    raw_perms = ["InvalidPerm", "RuleRead"]
    converted = convert_permissions(raw_perms)
    assert len(converted) == 1
    assert Permission.RULE_READ in converted

    # Test empty list
    assert convert_permissions([]) == []


def test_perms():
    """Test the perms function for creating permission specifications"""
    # Test any_of
    result = perms(any_of=[Permission.RULE_READ, Permission.POLICY_READ])
    assert "any_of" in result
    assert len(result["any_of"]) == 2
    assert "View Rules" in result["any_of"]
    assert "View Policies" in result["any_of"]

    # Test all_of
    result = perms(all_of=[Permission.RULE_READ, Permission.POLICY_READ])
    assert "all_of" in result
    assert len(result["all_of"]) == 2
    assert "View Rules" in result["all_of"]
    assert "View Policies" in result["all_of"]

    # Test both any_of and all_of
    result = perms(any_of=[Permission.RULE_READ], all_of=[Permission.POLICY_READ])
    assert "any_of" in result
    assert "all_of" in result
    assert len(result["any_of"]) == 1
    assert len(result["all_of"]) == 1

    # Test with string values
    result = perms(any_of=["View Rules", "View Policies"])
    assert "any_of" in result
    assert len(result["any_of"]) == 2
    assert "View Rules" in result["any_of"]
    assert "View Policies" in result["any_of"]


def test_any_perms():
    """Test the any_perms function"""
    result = any_perms(Permission.RULE_READ, Permission.POLICY_READ)
    assert "any_of" in result
    assert len(result["any_of"]) == 2
    assert "View Rules" in result["any_of"]
    assert "View Policies" in result["any_of"]


def test_all_perms():
    """Test the all_perms function"""
    result = all_perms(Permission.RULE_READ, Permission.POLICY_READ)
    assert "all_of" in result
    assert len(result["all_of"]) == 2
    assert "View Rules" in result["all_of"]
    assert "View Policies" in result["all_of"]


def test_permission_builder():
    """Test the PermissionBuilder class"""
    builder = PermissionBuilder()

    # Test require
    result = builder.require(Permission.RULE_READ, Permission.POLICY_READ).build()
    assert "permissions" in result
    assert "all_of" in result["permissions"]
    assert len(result["permissions"]["all_of"]) == 2
    assert "View Rules" in result["permissions"]["all_of"]
    assert "View Policies" in result["permissions"]["all_of"]

    # Test require_any
    result = builder.require_any(Permission.RULE_READ, Permission.POLICY_READ).build()
    assert "permissions" in result
    assert "any_of" in result["permissions"]
    assert len(result["permissions"]["any_of"]) == 2
    assert "View Rules" in result["permissions"]["any_of"]
    assert "View Policies" in result["permissions"]["any_of"]

    # Test with_annotation
    result = (
        builder.require(Permission.RULE_READ)
        .with_annotation("rate_limit", {"requests": 100, "period": "1m"})
        .build()
    )
    assert "permissions" in result
    assert "rate_limit" in result
    assert result["rate_limit"] == {"requests": 100, "period": "1m"}

    # Test method chaining
    result = (
        builder.require(Permission.RULE_READ)
        .with_annotation("key1", "value1")
        .with_annotation("key2", "value2")
        .build()
    )
    assert "permissions" in result
    assert "key1" in result
    assert "key2" in result
    assert result["key1"] == "value1"
    assert result["key2"] == "value2"


def test_requires_permissions():
    """Test the requires_permissions function"""
    builder = requires_permissions()
    assert isinstance(builder, PermissionBuilder)

    # Test the builder instance works
    result = builder.require(Permission.RULE_READ).build()
    assert "permissions" in result
    assert "all_of" in result["permissions"]
    assert len(result["permissions"]["all_of"]) == 1
    assert "View Rules" in result["permissions"]["all_of"]


def test_permission_builder_edge_cases():
    """Test edge cases for PermissionBuilder"""
    builder = PermissionBuilder()

    # Test empty permissions
    result = builder.require().build()
    assert "permissions" in result
    assert "all_of" in result["permissions"]
    assert len(result["permissions"]["all_of"]) == 0

    # Test multiple calls to require
    result = (
        builder.require(Permission.RULE_READ).require(Permission.POLICY_READ).build()
    )
    assert "permissions" in result
    assert "all_of" in result["permissions"]
    assert len(result["permissions"]["all_of"]) == 1  # Last require overwrites previous

    # Test multiple calls to require_any
    result = (
        builder.require_any(Permission.RULE_READ)
        .require_any(Permission.POLICY_READ)
        .build()
    )
    assert "permissions" in result
    assert "any_of" in result["permissions"]
    assert (
        len(result["permissions"]["any_of"]) == 1
    )  # Last require_any overwrites previous
