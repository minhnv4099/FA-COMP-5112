#
#

#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from src.mcp.client import MCPClient
from mcp.types import Tool
from mcp.client.session import ClientSession
import asyncio
from concurrent.futures import Future

from langchain.tools.tool_node import InjectedState


def tool_schemas_from_mcp_client(client: MCPClient):
    tools = asyncio.run(client.list_tools())
    tool_schemas = []

    for tool in tools:
        des = tool.description
        input_schema = tool.inputSchema
        output_schema = tool.outputSchema

