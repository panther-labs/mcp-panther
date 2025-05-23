import asyncio

from agent import Agent


async def main():
    """
    This is a simple chatbot that uses the Agent class to converse with the user.
    """
    agent = Agent(name="Chatbot", mcp=None)
    await agent.initialize()

    user_input = input("Enter a message: ")
    while user_input:
        await agent.converse(user_input)
        user_input = input("Enter a message: ")


if __name__ == "__main__":
    asyncio.run(main())
