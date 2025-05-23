# Agent Framework

A Bedrock-powered agent framework for building AI assistants with tool-calling capabilities using MCP (Machine Callable Program).

## Overview

The Agent class provides a simple interface for creating AI assistants that can:
- Engage in natural language conversations
- Access and utilize tools through MCP
- Chain together multiple tool calls
- Maintain conversation context

## Usage

Set up your AWS credentials for Bedrock access and Panther API keys in the .env file.  See .env.sample for examples.

## Agent Configuration

- `name`: The name of the agent (default: "Agent")
- `model`: The Bedrock model to use (default: anthropic.claude-3-5-sonnet-20240620-v1:0)
- `system_prompt`: Custom system prompt to control agent behavior
- `mcp`: The FastMCP server instance for tool access
- `requested_tools`: List of specific tools to enable (if None, all tools are used)

## Examples

The `agent/` directory contains several example implementations:

### Simple Chatbot (chatbot.py)
A basic chatbot that converses with the user without using any tools.

### Agent Conversation (agent_convo.py)
Demonstrates two agents having a conversation with one another, with one agent having access to tools.

### SPL Converter (spl_converter.py)
A specialized agent that converts Splunk SPL queries to Panther detection rules using multiple tools and a structured workflow.

## Advanced Features

### Tool Configuration
The Agent class automatically converts MCP tools to Bedrock tool configurations through the `get_tool_config()` method.

### Tool Calling
When an agent wants to use a tool, the framework handles the interaction through the `mcp_call_tool()` method.

## Running the Examples

```bash
# Simple Chatbot
python agent/chatbot.py

# Agent Conversation
python agent/agent_convo.py

# SPL Converter
python agent/spl_converter.py path/to/splunk_rule.yml
```
