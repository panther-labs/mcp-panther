"""
Prompt templates for guiding users through Panther alert triage workflows.
"""

from .registry import mcp_prompt


@mcp_prompt
def get_log_sources_report() -> str:
    return """You are an expert in security data pipelines and ETL. Your goal is to ensure that all Panther log sources are healthy, and if they are unhealthy, to understand the root cause and how to fix it. Follow these steps:

1. List log sources
2. If any log sources are unhealthy, search for a related SYSTEM ERROR alert, you might need to look a few weeks back if the source has been unhealthy for some time.
3. If the reason for being unhealthy is a classification error, query the panther_monitor.public. database, classification_failures table with a filter on p_source_id matching the offending source. Read the payload, try to guess the log type, and then compare it to the log source's attached schemas to pinpoint why it isn't classifying.
4. If no sources are unhealthy, print a summary of your findings. If several are unhealthy, triage one at a time, providing a summary for each one."""


@mcp_prompt
def list_detection_rule_errors(start_date: str, end_date: str) -> str:
    """Get all detection rule errors between the specified dates.

    Args:
        start_date: The start date in format "YYYY-MM-DD HH:MM:SSZ" (e.g. "2025-04-22 22:37:41Z")
        end_date: The end date in format "YYYY-MM-DD HH:MM:SSZ" (e.g. "2025-04-22 22:37:41Z")
    """
    return f"""You are an expert Python software developer specialized in cybersecurity and Panther. Your goal is to perform root cause analysis on detection errors and guide the human on how to resolve them with suggestions. This will guarantee a stable rule processor for security log analysis. Search for errors created between {start_date} and {end_date}. Use a concise, professional, informative tone."""


@mcp_prompt
def list_and_prioritize_alerts(start_date: str, end_date: str) -> str:
    """Get temporal alert data between specified dates and perform detailed actor-based analysis and prioritization.

    Args:
        start_date: The start date in format "YYYY-MM-DD HH:MM:SSZ" (e.g. "2025-04-22 22:37:41Z")
        end_date: The end date in format "YYYY-MM-DD HH:MM:SSZ" (e.g. "2025-04-22 22:37:41Z")
    """
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
