from enum import Enum
from typing import List, Dict, Optional, Union, Any


class Permission(Enum):
    """Panther permissions that can be required for tools."""

    ALERT_MODIFY = "Manage Alerts"
    ALERT_READ = "View Alerts"
    DATA_ANALYTICS_READ = "Query Data Lake"
    LOG_SOURCE_READ = "View Log Sources"
    ORGANIZATION_API_TOKEN_READ = "Read API Token Info"
    POLICY_READ = "View Policies"
    RULE_MODIFY = "Manage Rules"
    RULE_READ = "View Rules"
    SUMMARY_READ = "View Overview"
    USER_READ = "View Users"


# Mapping from raw values to enum values
RAW_TO_TITLE = {
    "RuleRead": Permission.RULE_READ,
    "RuleModify": Permission.RULE_MODIFY,
    "PolicyRead": Permission.POLICY_READ,
    "UserRead": Permission.USER_READ,
    "DataAnalyticsRead": Permission.DATA_ANALYTICS_READ,
    "AlertRead": Permission.ALERT_READ,
    "AlertModify": Permission.ALERT_MODIFY,
    "SummaryRead": Permission.SUMMARY_READ,
    "LogSourceRead": Permission.LOG_SOURCE_READ,
    "OrganizationAPITokenRead": Permission.ORGANIZATION_API_TOKEN_READ,
}


def convert_permissions(permissions: List[str]) -> List[Permission]:
    """
    Convert a list of raw permission strings to their title-based enum values.
    Any unrecognized permissions will be skipped.

    Args:
        permissions: List of raw permission strings (e.g. ["RuleRead", "PolicyRead"])

    Returns:
        List of Permission enums with title values
    """
    return [RAW_TO_TITLE[perm] for perm in permissions if perm in RAW_TO_TITLE]


def perms(
    any_of: Optional[List[Union[Permission, str]]] = None,
    all_of: Optional[List[Union[Permission, str]]] = None,
) -> Dict[str, List[str]]:
    """
    Create a permissions specification dictionary.

    Args:
        any_of: List of permissions where any one is sufficient
        all_of: List of permissions where all are required

    Returns:
        Dict with 'any_of' and/or 'all_of' keys mapping to permission lists
    """
    result = {}
    if any_of is not None:
        result["any_of"] = [p if isinstance(p, str) else p.value for p in any_of]

    if all_of is not None:
        result["all_of"] = [p if isinstance(p, str) else p.value for p in all_of]

    return result


def any_perms(*permissions: Union[Permission, str]) -> Dict[str, List[str]]:
    """
    Create a permissions specification requiring any of the given permissions.

    Args:
        *permissions: Variable number of permissions where any one is sufficient

    Returns:
        Dict with 'any_of' key mapping to the permission list
    """
    return perms(any_of=list(permissions))


def all_perms(*permissions: Union[Permission, str]) -> Dict[str, List[str]]:
    """
    Create a permissions specification requiring all of the given permissions.

    Args:
        *permissions: Variable number of permissions where all are required

    Returns:
        Dict with 'all_of' key mapping to the permission list
    """
    return perms(all_of=list(permissions))


class PermissionBuilder:
    """
    A builder class for creating permission specifications with a fluent interface.

    Example:
        ```python
        @mcp_tool(annotations=requires_permissions()
            .require_any(Permission.ALERT_READ)
            .with_annotation("rate_limit", {"requests": 100, "period": "1m"})
            .build())
        ```
    """

    def __init__(self):
        self._annotations = {}

    def require(self, *permissions: Union[Permission, str]) -> "PermissionBuilder":
        """
        Require all of the given permissions.

        Args:
            *permissions: Variable number of permissions where all are required

        Returns:
            Self for method chaining
        """
        self._annotations["permissions"] = all_perms(*permissions)
        return self

    def require_any(self, *permissions: Union[Permission, str]) -> "PermissionBuilder":
        """
        Require any of the given permissions.

        Args:
            *permissions: Variable number of permissions where any one is sufficient

        Returns:
            Self for method chaining
        """
        self._annotations["permissions"] = any_perms(*permissions)
        return self

    def with_annotation(self, key: str, value: Any) -> "PermissionBuilder":
        """
        Add any additional annotation.

        Args:
            key: The annotation key
            value: The annotation value

        Returns:
            Self for method chaining
        """
        self._annotations[key] = value
        return self

    def build(self) -> Dict[str, Any]:
        """
        Get the final annotations dictionary.

        Returns:
            Dict containing all annotations
        """
        return self._annotations


def requires_permissions() -> PermissionBuilder:
    """
    Start building permission requirements.

    Returns:
        A new PermissionBuilder instance

    Example:
        ```python
        @mcp_tool(annotations=requires_permissions()
            .require_any(Permission.ALERT_READ)
            .build())
        ```
    """
    return PermissionBuilder()
