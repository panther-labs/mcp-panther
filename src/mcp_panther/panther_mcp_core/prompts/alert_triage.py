"""
Prompt templates for guiding users through Panther alert triage workflows.
"""

from .registry import mcp_prompt


@mcp_prompt(
    name="get-detection-rule-errors",
    description="Find detection rule errors between the specified dates (YYYY-MM-DD HH:MM:SSZ format) and perform root cause analysis.",
    tags={"triage"},
)
def get_detection_rule_errors(start_date: str, end_date: str) -> str:
    return f"""You are an expert Python software developer specialized in cybersecurity and Panther. Your goal is to perform root cause analysis on detection errors and guide the human on how to resolve them with suggestions. This will guarantee a stable rule processor for security log analysis. Search for errors created between {start_date} and {end_date}. Use a concise, professional, informative tone."""


@mcp_prompt(
    name="prioritize-open-alerts",
    description="Performs detailed actor-based analysis and prioritization in the specified time period (YYYY-MM-DD HH:MM:SSZ format).",
    tags={"triage"},
)
def prioritize_open_alerts(start_date: str, end_date: str) -> str:
    return f"""Analyze open alerts and group them based on entity names. The goal is to identify patterns of related activity across alerts to be triaged together.

1. Find all alerts between {start_date} and {end_date}.
2. Summarize alert events and group them by entity names, combining similar alerts together.
3. For each group:
    1. Identify the actor performing the actions and the target of the actions
    2. Summarize the activity pattern across related alerts
    3. Include key details such as rule IDs triggered, timeframes of activity, source IPs and usernames, and systems or platforms affected
    4. Provide an assessment of whether the activity appears to be expected/legitimate or suspicious/concerning behavior requiring investigation. Specify a confidence level on a scale of 1-100.
    5. Think about the questions that would increase confidence in the assessment and incorporate them into next steps.

Format your response with clear markdown headings for each entity group and use concise, cybersecurity-nuanced language."""


@mcp_prompt(
    name="investigate-actor-activity",
    description="Performs an exhaustive investigation of a specific actor’s activity, including both alerted and non-alerted events, and produces a comprehensive final report with confidence assessment.",
    tags={"triage", "investigation"},
)
def investigate_actor_activity(actor: str) -> str:
    return f"""As a follow-up to the actor-based alert prioritization, perform an exhaustive investigation of all activity associated with the actor "{actor}". Go beyond the initial alert events and include any related activity that did not trigger alerts but may be relevant.

Instructions:
- Search for all events and signals (both alerted and non-alerted) involving "{actor}".
- Correlate these events to identify patterns, anomalies, or noteworthy behaviors.
- Summarize all findings, including timelines, systems accessed, actions performed, and any connections to other entities or incidents.
- Highlight any new evidence discovered that either increases or decreases your confidence in the assessment of this actor’s behavior.
- Provide a comprehensive final report with clear sections:
    - Executive Summary
    - Timeline of Activity
    - Notable Findings
    - Confidence Assessment (with justification)
    - Recommendations for next steps

When querying, use time-sliced queries to avoid scanning excess data. Use a concise, professional, and cybersecurity-focused tone. Format your response using markdown for clarity."""
