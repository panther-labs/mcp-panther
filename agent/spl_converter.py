import argparse
import asyncio

from agent import Agent
from src.mcp_panther.server import mcp

REQUESTED_TOOLS = [
    "get_log_type_schema_details",
    "list_log_type_schemas",
    "list_databases",
    "list_tables_for_database",
    "get_table_columns",
    "get_tables_for_database",
    "execute_data_lake_query",
    "get_data_lake_query_results",
    "get_sample_log_events",
]

SYSTEM_PROMPT = """
You are an expert detection engineer, specializing in converting Splunk rules to Panther rules.

Your workflow is as follows:
1. Analyze the Splunk rule to determine if it would be best implemented as a streaming Python rule or a scheduled SQL rule.
2. Look up the log type schema details to determine the appropriate log type and field mappings from Splunk to Panther.
3. Generate the appropriate Panther rule in Python or SQL based on the analysis.
"""


async def main(rule_file: str):
    agent = Agent(
        name="Spl Converter",
        mcp=mcp,
        requested_tools=REQUESTED_TOOLS,
        system_prompt=SYSTEM_PROMPT,
    )
    await agent.initialize()

    step1_prompt = "First, analyze the Splunk rule to determine if it would be best implemented as a streaming Python rule or a scheduled SQL rule."
    with open("agent/prompts/python_vs_sql.md", "r") as file:
        context = file.read()
    with open(rule_file, "r") as file:
        rule = file.read()

    step1_content = [
        {"text": step1_prompt},
        {"text": context},
        {"text": rule},
    ]

    await agent.converse(step1_content)

    step2_prompt = "Next, look up the log type schema details to determine the appropriate log type and field mappings from Splunk to Panther."
    await agent.converse(step2_prompt)

    step3_prompt = "Finally, generate the appropriate Panther rule in Python or SQL based on the analysis."
    await agent.converse(step3_prompt)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert Splunk rules to Panther rules"
    )
    parser.add_argument("rule_file", help="Path to the Splunk rule file")
    args = parser.parse_args()

    asyncio.run(main(args.rule_file))
