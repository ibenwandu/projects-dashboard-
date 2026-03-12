#!/usr/bin/env python
"""Cursor MCP Server - Exposes Cursor Cloud Agents API as native MCP tools."""

import asyncio
import json
import sys
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, CallToolResult
from cursor_client import CursorAgentsClient


# Initialize server (client initialized lazily when tools are called)
server = Server("cursor-agents")
client = None


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    return [
        Tool(
            name="launch_cursor_agent",
            description="Submit a coding task to Cursor AI",
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "The coding instruction (e.g., 'Refactor this function to use list comprehension: [code]')"
                    },
                    "repo": {
                        "type": "string",
                        "description": "GitHub repo in 'owner/name' format (optional)"
                    },
                    "model": {
                        "type": "string",
                        "description": "Model name: claude-sonnet, gpt-4o, gemini-2-pro, etc. (optional, uses account default)"
                    }
                },
                "required": ["task"]
            }
        ),
        Tool(
            name="get_agent_status",
            description="Check if a Cursor agent has finished and retrieve results",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "Agent ID from launch_cursor_agent response"
                    }
                },
                "required": ["agent_id"]
            }
        ),
        Tool(
            name="list_agents",
            description="List all recent agents (running, completed, errored)",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return (default 10)",
                        "default": 10
                    }
                }
            }
        ),
        Tool(
            name="send_followup",
            description="Add follow-up instructions to a running or completed agent",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "Agent ID"
                    },
                    "message": {
                        "type": "string",
                        "description": "Follow-up prompt"
                    }
                },
                "required": ["agent_id", "message"]
            }
        ),
        Tool(
            name="download_artifact",
            description="Fetch generated code or file content from a completed agent",
            inputSchema={
                "type": "object",
                "properties": {
                    "artifact_url": {
                        "type": "string",
                        "description": "URL from get_agent_status artifacts list"
                    }
                },
                "required": ["artifact_url"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool invocation."""
    global client
    try:
        # Initialize client lazily (only when tools are first called)
        if client is None:
            client = CursorAgentsClient()
        if name == "launch_cursor_agent":
            result = await client.launch(
                task=arguments["task"],
                repo=arguments.get("repo"),
                model=arguments.get("model")
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "get_agent_status":
            result = await client.get_status(agent_id=arguments["agent_id"])
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "list_agents":
            limit = arguments.get("limit", 10)
            result = await client.list(limit=limit)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "send_followup":
            result = await client.send_followup(
                agent_id=arguments["agent_id"],
                message=arguments["message"]
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "download_artifact":
            result = await client.download_artifact(artifact_url=arguments["artifact_url"])
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        error_text = f"Error in {name}: {str(e)}"
        return [TextContent(type="text", text=error_text)]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
