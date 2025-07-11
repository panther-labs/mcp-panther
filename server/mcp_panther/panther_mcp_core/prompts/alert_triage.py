"""
Prompt templates for guiding users through Panther alert triage workflows.
"""

from .registry import mcp_prompt


@mcp_prompt(
    name="Get Detection Rule Errors",
    description="Find detection rule errors between the specified dates (YYYY-MM-DD HH:MM:SSZ format) and perform root cause analysis on them.",
    tags={"triage", "operations"},
)
def get_detection_rule_errors(start_date: str, end_date: str) -> str:
    return f"""You are an expert Python software developer specialized in cybersecurity and Panther. Your goal is to perform root cause analysis on detection errors and guide the human on how to resolve them with suggestions. This will guarantee a stable rule processor for security log analysis. Search for errors created between {start_date} and {end_date}. Use a concise, professional, informative tone."""


@mcp_prompt(
    name="List and Prioritize Alerts",
    description="Find commonalities between alerts in the specified time period (YYYY-MM-DD HH:MM:SSZ format) and perform detailed actor-based analysis and prioritization.",
    tags={"triage"},
)
def list_and_prioritize_alerts(start_date: str, end_date: str) -> str:
    return f"""Analyze alert signals and group them based on entity names. The goal is to identify patterns of related activity across alerts and triage them together.

1. Get all alert IDs between {start_date} and {end_date}.
2. Get stats on all alert events with the summarize_alert_events tool.
3. Group alerts by entity names, combining similar alerts together.
4. For each group:
    1. Identify the common entity name performing the actions
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
    5. End with prioritized recommendations for investigation based on the entity groups, not just alert severity.

Format your response with clear markdown headings for each entity group and use concise, cybersecurity-nuanced language."""
