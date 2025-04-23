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
    """
    return f"""You are an expert cyber security analyst. Follow these steps to triage a Panther alert:
    1. Get the alert details for alert ID {alert_id}
    2. Query the data lake to read all associated events (database: panther_rule_matches.public, table: log type from the alert)
    3. Determine alert judgment based on common attacker patterns and techniques (benign, false positive, true positive, or a custom judgment).
    """


@mcp_prompt
def list_and_prioritize_alerts(start_date: str, end_date: str) -> str:
    """Get temporal alert data between specified dates and perform detailed actor-based analysis and prioritization.

    Args:
        start_date: The start date in format "YYYY-MM-DD HH:MM:SSZ" (e.g. "2025-04-22 22:37:41Z")
        end_date: The end date in format "YYYY-MM-DD HH:MM:SSZ" (e.g. "2025-04-22 22:37:41Z")
    """
    return f"""Analyze Temporal Alert Data between {start_date} and {end_date}, grouping them logically based on actor patterns rather than just by severity or rule type. For each group:

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
