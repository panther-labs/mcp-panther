"""
Prompt templates for guiding users through Panther alert triage workflows.
"""

from .registry import mcp_prompt


@mcp_prompt
def triage_alert(alert_id: str) -> str:
    """
    Generate a prompt for triaging a specific Panther alert.

    Args:
        alert_id: The ID of the alert to triage

    Returns:
        A prompt string for guiding the user through alert triage
    """
    return f"""You are an expert cyber security analyst. Follow these steps to triage a Panther alert:
    1. Get the alert details for alert ID {alert_id}
    2. Query the data lake to read all associated events (database: panther_rule_matches.public, table: log type from the alert)
    3. Determine alert judgment based on common attacker patterns and techniques (benign, false positive, true positive, or a custom judgment).
    """


@mcp_prompt
def prioritize_and_triage_alerts() -> str:
    """
    Generate a prompt for prioritizing and triaging multiple Panther alerts.

    Returns:
        A prompt string for guiding the user through alert prioritization and triage
    """
    return """You are an expert cyber security analyst. Your goal is to prioritize alerts based on severity, impact, and other relevant criteria to decide which alerts to investigate first. Use the following steps to prioritize alerts:
    1. List all alerts in the last 7 days excluding severities LOW, and logically group them by user, host, or other similar criteria. Alerts can be related even if they have different titles or log types (for example, if a user logs into Okta and then AWS).
    2. Triage each group of alerts to understand what happened and what the impact was. Query the data lake to read all associated events (database: panther_rule_matches.public, table: log type from the alert) and use the results to understand the impact.
    3. For each group, if the alerts are false positives, suggest a rule improvement by reading the Python source, comment on the alert with your analysis, and mark the alert as invalid. If the alerts are true positives, begin pivoting on the available data to understand the root cause and impact.
    """
