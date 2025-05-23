import json
import os
import sys
from typing import List

import boto3
from dotenv import load_dotenv
from fastmcp import Client, FastMCP

# Correctly add the project root to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from src.mcp_panther.server import mcp

# Load environment variables from .env file
load_dotenv()


MODEL = "anthropic.claude-3-5-sonnet-20240620-v1:0"


class Agent:
    """
    This is the Agent class that is used to create an agent.  It uses Bedrock to generate responses and can call MCP tools.
    Args:
        name: The name of the agent.
        model: The Bedrock model to use for the agent.
        system_prompt: The system prompt to use for the agent.
        mcp: The MCP server to use for the agent.  Defaults to the MCP server in the src/mcp_panther/server.py file.
        requested_tools: The tools to use for the agent.  If not provided, all tools will be used.
    """

    def __init__(
        self,
        name: str = "Agent",
        model: str = MODEL,
        system_prompt: str = None,
        mcp: FastMCP = mcp,
        requested_tools: List[str] = None,
    ):
        self.name = name
        self.model = model
        self.system_prompt = system_prompt
        self.conversation = []
        self.mcp = mcp
        self.requested_tools = requested_tools
        self.mcp_client = None
        self.tool_config = None
        self.bedrock_client = boto3.client("bedrock-runtime")

    async def initialize(self):
        if self.mcp:
            self.mcp_client = Client(self.mcp)
            self.tool_config = await self.get_tool_config(self.requested_tools)
        return self

    async def converse(self, content: dict):
        if not isinstance(content, list):
            content = (
                [{"text": content}]
                if isinstance(content, str)
                else [{"text": str(content)}]
            )
        self.conversation.append({"role": "user", "content": content})

        # Call Bedrock API
        converse_kwargs = {"modelId": self.model, "messages": self.conversation}
        if self.mcp_client:
            converse_kwargs["toolConfig"] = self.tool_config
        if self.system_prompt:
            converse_kwargs["system"] = [{"text": self.system_prompt}]
        response = self.bedrock_client.converse(**converse_kwargs)

        # Extract response information
        message = response["output"]["message"]
        stop_reason = response["stopReason"]

        # Ensure message has proper structure
        if "content" not in message or message["content"] is None:
            message["content"] = []

        self.conversation.append(message)

        # Print text content for debugging
        for content_item in message["content"]:
            if "text" in content_item:
                print(f"\n\n{self.name}: {content_item['text']}")

        # Process tool use if needed
        if stop_reason == "tool_use":
            tool_results = []
            for content_item in message["content"]:
                if "toolUse" in content_item:
                    tool_call = content_item["toolUse"]
                    print(f"\n\n{self.name}: Calling tool {tool_call['name']}")
                    result = await self.mcp_call_tool(tool_call)
                    tool_results.append(
                        {
                            "toolResult": {
                                "toolUseId": tool_call["toolUseId"],
                                "content": [{"json": result}],
                            }
                        }
                    )

            return await self.converse(tool_results)
        else:
            return message["content"]

    async def get_tool_config(self, requested_tools: List[str] = None) -> dict:
        """
        Convert a list of MCP Tool objects to a Bedrock tool config.
        """
        async with self.mcp_client as client:
            tools = await client.list_tools()
        if requested_tools:
            tools = [tool for tool in tools if tool.name in requested_tools]
        tool_config = {"tools": []}
        for tool in tools:
            tool = tool.model_dump()
            tool["inputSchema"] = {"json": tool["inputSchema"]}
            tool.pop("annotations")
            tool_config["tools"].append({"toolSpec": tool})
        return tool_config

    async def mcp_call_tool(self, tool_call: dict) -> dict:
        """
        Invoke an MCP tool from a Bedrock tool use.
        """
        tool_name = tool_call["name"]
        tool_input = tool_call["input"]

        async with self.mcp_client as client:
            result = await client.call_tool(tool_name, tool_input)
        result = result[0]
        result = result.model_dump()
        result = result["text"]
        result = json.loads(result)
        return result
