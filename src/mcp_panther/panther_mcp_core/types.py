from enum import Enum


class AlertSeverity(Enum):
    """Enum representing Panther alert severity levels."""

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatus(Enum):
    """Enum representing Panther alert statuses."""

    OPEN = "OPEN"
    TRIAGED = "TRIAGED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class AlertType(Enum):
    """Enum representing Panther alert types."""

    ALERT = "ALERT"
    DETECTION_ERROR = "DETECTION_ERROR"
    SYSTEM_ERROR = "SYSTEM_ERROR"


class AlertSubtype(Enum):
    """Enum representing Panther alert subtypes."""

    # Alert subtypes
    POLICY = "POLICY"
    RULE = "RULE"
    SCHEDULED_RULE = "SCHEDULED_RULE"

    # Detection error subtypes
    RULE_ERROR = "RULE_ERROR"
    SCHEDULED_RULE_ERROR = "SCHEDULED_RULE_ERROR"

    @classmethod
    def get_valid_subtypes_for_type(cls, alert_type: AlertType) -> list["AlertSubtype"]:
        """Get the valid subtypes for a given alert type."""
        valid_subtypes = {
            AlertType.ALERT: [
                cls.POLICY,
                cls.RULE,
                cls.SCHEDULED_RULE,
            ],
            AlertType.DETECTION_ERROR: [
                cls.RULE_ERROR,
                cls.SCHEDULED_RULE_ERROR,
            ],
            AlertType.SYSTEM_ERROR: [],
        }
        return valid_subtypes.get(alert_type, [])
