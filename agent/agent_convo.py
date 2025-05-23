import asyncio

from agent import Agent

from src.mcp_panther.server import mcp

REQUESTED_TOOLS = [
    "get_log_type_schema_details",
    "list_log_type_schemas",
    "list_databases",
]

async def main():
    """
    This is a simple conversation between two agents.
    """
    agent1 = Agent(
        name="CISO",
        system_prompt="You are a CISO of a company.  You are having a conversation with a SOC manager.  The SOC manager is also your mother in law.  Your wife is also the CEO of the company.  When you are ready to end the conversation, say 'end_conversation'.",
        mcp=None,
    )
    agent2 = Agent(
        name="SOC Manager",
        system_prompt="You are a SOC manager.  You are having a conversation with a CISO.  The CISO is also your son in law.  You have a strained relationship due to his relationship with your daughter.  When you are ready to end the conversation, say 'end_conversation'.",
        mcp=mcp,
        requested_tools=REQUESTED_TOOLS,
    )

    await agent1.initialize()
    await agent2.initialize()

    # Initial message to start conversation
    initial_message = "We've been hacked.  What should we do?"
    response = await agent1.converse(initial_message)

    # Continue conversation until one agent ends it
    while True:
        if not response or check_for_end_conversation(response):
            break

        response = await agent2.converse(response)

        if not response or check_for_end_conversation(response):
            break

        response = await agent1.converse(response)


def check_for_end_conversation(content):
    """Check if the content contains the end_conversation signal"""
    if not content or not isinstance(content, list):
        return True

    for item in content:
        if (
            isinstance(item, dict)
            and "text" in item
            and "end_conversation" in item["text"]
        ):
            return True
    return False


if __name__ == "__main__":
    asyncio.run(main())
