from enum import Enum
from typing import Dict, List, Optional, Union


class Permission(Enum):
    """Panther permissions that can be required for tools."""

    # Alert permissions
    ALERT_READ = "Read Alerts"
    ALERT_MODIFY = "Manage Alerts"

    # Policy permissions
    POLICY_READ = "View Policies"
    POLICY_MODIFY = "Manage Policies"

    # Resource permissions
    RESOURCE_READ = "ResourceRead"  # Not in UI mapping, keeping raw value
    RESOURCE_MODIFY = "ResourceModify"  # Not in UI mapping, keeping raw value

    # Rule permissions
    RULE_READ = "View Rules"
    RULE_MODIFY = "Manage Rules"

    # Summary/metrics permissions
    SUMMARY_READ = "Read Panther Metrics"

    # Bulk upload permissions
    BULK_UPLOAD = "Bulk Upload"
    BULK_UPLOAD_VALIDATE = "Bulk Upload Validate"

    # User permissions
    USER_READ = "Read User Info"
    USER_MODIFY = "Manage Users"

    # API Token permissions
    ORGANIZATION_API_TOKEN_READ = "Read API Token Info"
    ORGANIZATION_API_TOKEN_MODIFY = "Manage API Tokens"

    # General settings permissions
    GENERAL_SETTINGS_READ = "Read Panther Settings Info"
    GENERAL_SETTINGS_MODIFY = (
        "GeneralSettingsModify"  # Not in UI mapping, keeping raw value
    )

    # Cloud security source permissions
    CLOUDSEC_SOURCE_READ = "View Cloud Security Sources"
    CLOUDSEC_SOURCE_MODIFY = "Manage Cloud Security Sources"

    # Log source permissions
    LOG_SOURCE_RAW_DATA_READ = (
        "LogSourceRawDataRead"  # Not in UI mapping, keeping raw value
    )
    LOG_SOURCE_READ = "View Log Sources"
    LOG_SOURCE_MODIFY = "Manage Log Sources"

    # Destination permissions
    DESTINATION_READ = "DestinationRead"  # Not in UI mapping, keeping raw value
    DESTINATION_MODIFY = "DestinationModify"  # Not in UI mapping, keeping raw value

    # Data analytics permissions
    DATA_ANALYTICS_READ = "Query Data Lake"
    DATA_ANALYTICS_MODIFY = "Manage Saved Searches"

    # Lookup permissions
    LOOKUP_READ = "LookupRead"  # Not in UI mapping, keeping raw value
    LOOKUP_MODIFY = "LookupModify"  # Not in UI mapping, keeping raw value

    # Panther AI permission
    RUN_PANTHER_AI = "Run Panther AI"


# Mapping from raw permission constants to human-readable titles
# The raw constants come from the backend, the titles are what the API returns
RAW_TO_PERMISSION = {
    "AlertRead": Permission.ALERT_READ,
    "AlertModify": Permission.ALERT_MODIFY,
    "PolicyRead": Permission.POLICY_READ,
    "PolicyModify": Permission.POLICY_MODIFY,
    "ResourceRead": Permission.RESOURCE_READ,
    "ResourceModify": Permission.RESOURCE_MODIFY,
    "RuleRead": Permission.RULE_READ,
    "RuleModify": Permission.RULE_MODIFY,
    "SummaryRead": Permission.SUMMARY_READ,
    "BulkUpload": Permission.BULK_UPLOAD,
    "BulkUploadValidate": Permission.BULK_UPLOAD_VALIDATE,
    "UserRead": Permission.USER_READ,
    "UserModify": Permission.USER_MODIFY,
    "OrganizationAPITokenRead": Permission.ORGANIZATION_API_TOKEN_READ,
    "OrganizationAPITokenModify": Permission.ORGANIZATION_API_TOKEN_MODIFY,
    "GeneralSettingsRead": Permission.GENERAL_SETTINGS_READ,
    "GeneralSettingsModify": Permission.GENERAL_SETTINGS_MODIFY,
    "CloudsecSourceRead": Permission.CLOUDSEC_SOURCE_READ,
    "CloudsecSourceModify": Permission.CLOUDSEC_SOURCE_MODIFY,
    "LogSourceRawDataRead": Permission.LOG_SOURCE_RAW_DATA_READ,
    "LogSourceRead": Permission.LOG_SOURCE_READ,
    "LogSourceModify": Permission.LOG_SOURCE_MODIFY,
    "DestinationRead": Permission.DESTINATION_READ,
    "DestinationModify": Permission.DESTINATION_MODIFY,
    "DataAnalyticsRead": Permission.DATA_ANALYTICS_READ,
    "DataAnalyticsModify": Permission.DATA_ANALYTICS_MODIFY,
    "LookupRead": Permission.LOOKUP_READ,
    "LookupModify": Permission.LOOKUP_MODIFY,
    "RunPantherAI": Permission.RUN_PANTHER_AI,
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
    return [
        RAW_TO_PERMISSION[perm] for perm in permissions if perm in RAW_TO_PERMISSION
    ]


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
