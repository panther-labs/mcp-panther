from .registry import mcp_prompt


@mcp_prompt(
    name="get-monthly-detection-quality-report",
    description="Generates a comprehensive detection quality report for analyzing alert data a given month and year to identify problematic rules and opportunities for improvement, including alerts, detection errors, and system errors.",
    tags={"reporting"},
)
def get_monthly_detection_quality_report(month: str, year: str) -> str:
    return f"""Build a comprehensive rule quality report for {month} {year} that includes:

SCOPE & DATA REQUIREMENTS:
- Analyze ALL alert types: Alerts, detection errors, and system errors
- Include severity breakdown but exclude INFO-level alerts
- Show alert status distribution
- Calculate unique alerts vs total volume 
- Identify any rules that generated errors during the period

ANALYSIS REQUIREMENTS:
- Top rules by alert volume with percentage of total
- Quality scoring methodology (1-10 scale) based on:
  * Alert volume optimization (25%) - 10-50 alerts/month is optimal
  * False positive rate (25%) - based on closed/total ratio  
  * Resolution efficiency (20%) - closure rate and time to resolution
  * Severity appropriateness (15%) - alignment with business impact
  * Signal cardinality (10%) - unique entities per alert
  * Error rate (5%) - detection errors generated
- Rule purpose/description for context
- Severity distribution analysis
- Status breakdown by severity level

OUTPUT FORMAT:
- Executive summary with key metrics and critical findings
- Detailed table with Rule ID, Name, Alert Count, % of Total, Severity, Unique Alerts, Quality Score
- Separate sections for detection errors and system errors
- Deep dive analysis of problematic rules (high volume, low quality)
- Highlight high-performing rules as examples
- Immediate action plan with specific recommendations
- Medium-term strategy for detection engineering improvements

CRITICAL ANALYSIS POINTS:
- Identify alert volume imbalances (rules generating >10% of total alerts)
- Flag INFO-level rules creating noise
- Calculate signal-to-noise ratios for high-volume rules
- Assess deduplication effectiveness
- Review rule error patterns and root causes
- Analyze temporal patterns and operational insights

Please provide specific, actionable recommendations with target metrics for improvement."""


@mcp_prompt(
    name="get-monthly-log-sources-report",
    description="Generates a monthly report on the health of all Panther log sources for a given month and year, and triages any unhealthy sources.",
    tags={"reporting"},
)
def get_monthly_log_sources_report(month: str, year: str) -> str:
    return f"""You are an expert in security log ingestion pipelines. Check the health of all Panther log sources for {month} {year}, and if they are unhealthy, understand the root cause and how to fix it. Follow these steps:

1. List log sources and their health status for {month} {year}.
2. If any log sources are unhealthy, search for a related SYSTEM alert for that source during {month} {year}. You may need to look a few weeks back within the month.
3. If the reason for being unhealthy is a classification error, query the panther_monitor.public.classification_failures table with a matching p_source_id for events in {month} {year}. Read the payload column and try to infer the log type based on the data, and then compare it to the log source's attached schemas to pinpoint why it isn't classifying.
4. If no sources are unhealthy, print a summary of your findings for {month} {year}. If several are unhealthy, triage one at a time, providing a summary for each one.

Be sure to scope all findings and queries to the specified month and year."""
