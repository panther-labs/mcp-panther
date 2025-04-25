"""
Prompt templates for guiding users through Panther alert triage workflows.
"""

from .registry import mcp_prompt


@mcp_prompt
def list_and_prioritize_alerts(start_date: str, end_date: str) -> str:
    """Get temporal alert data between specified dates and perform detailed actor-based analysis and prioritization.

    Args:
        start_date: The start date in format "YYYY-MM-DD HH:MM:SSZ" (e.g. "2025-04-22 22:37:41Z")
        end_date: The end date in format "YYYY-MM-DD HH:MM:SSZ" (e.g. "2025-04-22 22:37:41Z")
    """
    return f"""Analyze Temporal Alerts and group them logically based on actor patterns rather than just by severity or rule type.

1. Get all alert IDs between {start_date} and {end_date} with the list_alerts tool
2. Get stats on all alert events with the get_temporal_alert_groups tool
3. Group alerts by actor patterns
4. For each group:
    1. Identify the common actor or entity performing the actions

    2. Summarize the activity pattern across all related alerts

    3. Include key details such as:
    - Rule IDs triggered
    - Timeframes of activity
    - Source IPs and usernames involved
    - Systems or platforms affected

    4. Provide a brief assessment of whether the activity appears to be:
    - Expected system behavior
    - Legitimate user activity
    - Suspicious or concerning behavior requiring investigation

    5. End with prioritized recommendations for investigation based on the actor groups, not just alert severity.

Format your response with clear headings for each actor group and use concise, security-focused language."""


@mcp_prompt
def get_alerts_by_timeframe(start_date: str, end_date: str) -> str:
    """Get a simple list of alerts created within a specified time period.

    Args:
        start_date: The start date in format "YYYY-MM-DD HH:MM:SSZ" (e.g. "2025-04-22 22:37:41Z")
        end_date: The end date in format "YYYY-MM-DD HH:MM:SSZ" (e.g. "2025-04-22 22:37:41Z")
    """
    return f"""List all alerts created between {start_date} and {end_date}.

Format the results in a table with the following columns:
1. Alert ID
2. Title
3. Severity
4. Creation time
5. Status

Sort the alerts by creation time (newest first) and group them by severity."""
