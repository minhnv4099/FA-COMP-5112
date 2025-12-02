#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import logging
import functools
import os.path

from typing import Optional, Any, Union
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.types import AnyUrl
from mcp.types import CallToolResult, ReadResourceResult, GetPromptResult
from contextlib import AsyncExitStack

logger = logging.getLogger("MCPClient")


class MCPClient:

    session: Optional[ClientSession]
    exit_stack: Optional[AsyncExitStack]
    server_script_path: str

    def __init__(
        self,
        session: Optional[ClientSession] = None,
        exit_stack: Optional[AsyncExitStack] = None,
        server_script_path: Optional[str] = None,
        **kwargs,
    ):
        # Initialize session and client objects
        self.session = session
        self.exit_stack = exit_stack or AsyncExitStack()
        self.server_script_path = server_script_path

    @staticmethod
    def check_session(func: callable):
        @functools.wraps(func)
        def wrapped_func(self, *args, **kwargs):
            if self.session is None:
                raise ValueError(f"The session is now None, call 'connect_to_server' to connect to server before calling '{func.__name__}'")
            return func(self, *args, **kwargs)

        return wrapped_func

    @check_session
    async def list_tools(self):
        """List available tools on server/client has access

        Returns:
            List of tools
        """
        response = await self.session.list_tools()
        tools = response.tools
        logger.info(f"[CLIENT] - Available TOOLS: {[tool.name for tool in tools]}")

        return tools

    @check_session
    async def list_resources(self):
        """List available resources on server/client has access

        Returns:
            List of resources
        """
        response = await self.session.list_resources()
        resources = response.resources
        logger.info(f"[CLIENT] - Available RESOURCES: {[resource.name for resource in resources]}")

        return resources

    @check_session
    async def list_prompts(self):
        """List available prompts on server/client has access

        Returns:
            List of prompts
        """
        response = await self.session.list_prompts()
        prompts = response.prompts
        logger.info(f"[CLIENT] - Available PROMPTS : {[prompt.name for prompt in prompts]}")

        return prompts

    @check_session
    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any]
    ) -> CallToolResult:
        """The top wrapper tool call of session

        Args:
            name: Name of tool
            arguments: Arguments feed to tool

        Returns:
            Call tool result with attributes `content` and `structuredContent`
        """
        return await self.session.call_tool(name=name, arguments=arguments)

    @check_session
    async def read_resource(self, uri: Union[str, AnyUrl]) -> ReadResourceResult:
        """The top wrapper read resource of session

        Args:
            uri: Uri to resource (resource://...)

        Returns:
            Including contents - list of TextResourceContents
        """
        if isinstance(uri, str):
            uri = AnyUrl(url=uri)

        return await self.session.read_resource(uri)

    @check_session
    async def get_prompt(
        self,
        name: str,
        arguments: dict[str, Any]
    ) -> GetPromptResult:
        """The top wrapper get prompt of session

        Args:
            name: Name of prompt
            arguments: Arguments feed to prompt func

        Returns:
            message: List of PromptMessage
        """
        return await self.session.get_prompt(name=name, arguments=arguments)

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server

        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        assert os.path.isfile(server_script_path)

        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        stdio, write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(stdio, write))

        await self.session.initialize()

        logger.info(f"[CLIENT] - Connected to Server at '{server_script_path}'")

    @check_session
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()
