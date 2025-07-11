from enum import Enum
from typing import Dict, List, Optional, Union


class Permission(Enum):
    """Panther permissions that can be required for tools."""

    ALERT_MODIFY = "Manage Alerts"
    ALERT_READ = "View Alerts"
    DATA_ANALYTICS_READ = "Query Data Lake"
    LOG_SOURCE_READ = "View Log Sources"
    METRICS_READ = "Read Panther Metrics"
    ORGANIZATION_API_TOKEN_READ = "Read API Token Info"
    POLICY_READ = "View Policies"
    RULE_MODIFY = "Manage Rules"
    RULE_READ = "View Rules"
    USER_READ = "View Users"


# Mapping from raw values to enum values
RAW_TO_TITLE = {
    "AlertModify": Permission.ALERT_MODIFY,
    "AlertRead": Permission.ALERT_READ,
    "DataAnalyticsRead": Permission.DATA_ANALYTICS_READ,
    "LogSourceRead": Permission.LOG_SOURCE_READ,
    "OrganizationAPITokenRead": Permission.ORGANIZATION_API_TOKEN_READ,
    "PolicyRead": Permission.POLICY_READ,
    "RuleModify": Permission.RULE_MODIFY,
    "RuleRead": Permission.RULE_READ,
    "SummaryRead": Permission.METRICS_READ,  # Allows reading data & alert metrics
    "UserRead": Permission.USER_READ,
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
