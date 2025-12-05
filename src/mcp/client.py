#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations

import asyncio
import logging
import functools
import os.path

from pydantic import BaseModel, create_model
from typing import Optional, Any, Union, Coroutine, final, TYPE_CHECKING

from langchain_core.tools import BaseTool, StructuredTool
from langchain_mcp_adapters.tools import convert_mcp_tool_to_langchain_tool
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.types import AnyUrl, Tool, Prompt
from mcp.types import CallToolResult, ReadResourceResult, GetPromptResult
from contextlib import AsyncExitStack

if TYPE_CHECKING:
    from langchain_core.messages import ToolMessage
    from langchain_core.tools.base import ToolCall

logger = logging.getLogger(__name__)


class MCPClientToolExecutor:

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
        # connet only one time
        self.is_connected = False
        # support creating a new one
        self.session = session
        self.exit_stack = exit_stack or AsyncExitStack()

        self.server_script_path = server_script_path
        self.run(self.connect_to_server(server_script_path))

        self._tools_dict: dict[str, Tool] = dict()
        """{name: Tool}"""
        self._prompts_dict: dict[str, Prompt] = dict()
        """{name: Prompt}"""

    @staticmethod
    @final
    def run(coro: Coroutine[Any, Any, Any]) -> Any:
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = asyncio.get_event_loop()

        return current_loop.run_until_complete(coro)

    @staticmethod
    def check_session(func: callable):
        @functools.wraps(func)
        def wrapped_func(self, *args, **kwargs):
            if self.session is None:
                raise ValueError(f"The session is now None, call 'connect_to_server' to connect to server before calling '{func.__name__}'")
            return func(self, *args, **kwargs)

        return wrapped_func

    @property
    def tools_dict(self):
        """Dict of {name: Tool}"""
        if not self._tools_dict:
            self.run(self.list_tools())

        return self._tools_dict

    @property
    def prompts_dict(self):
        """Dict of {name: Prompt}"""
        if not self._prompts_dict:
            self.run(self.list_prompts())

        return self._prompts_dict

    @property
    def tools(self) -> list[Tool]:
        """A list of Tools"""
        return list(self.tools_dict.values())

    @property
    def prompts(self) -> list[Prompt]:
        """A list of Prompts"""
        return list(self.prompts_dict.values())

    @property
    def tool_names(self):
        """A list of tool names"""
        return list(self.tools_dict.keys())

    @property
    def prompt_names(self):
        """A list of prompt names"""
        return list(self.prompts_dict.keys())

    def get_mcp_tool(self, name: str) -> Tool:
        """Get a MCP tool"""
        if name not in self.tool_names:
            logger.info(f"Available tool names: {self.tool_names}")
            raise ValueError(f"No tool name {name!r}") from None

        return self.tools_dict[name]

    def get_mcp_prompt(self, name: str) -> Prompt:
        """Get a MCP prompt"""
        if name not in self.prompt_names:
            logger.info(f"Available prompt names: {self.prompt_names!r}")
            raise ValueError(f"No prompt name {name!r}") from None

        return self.prompts_dict[name]

    def mcp_tool_to_langchain_tool(self, tool: Tool) -> Union[BaseTool, StructuredTool]:
        """Convert a mcp tool to langchain tool. Also change ``args_schema`` from `dict` to `BaseModel`"""
        structured_tool = convert_mcp_tool_to_langchain_tool(tool=tool, session=self.session)
        properties = structured_tool.args_schema['properties']

        structured_tool.args_schema = self.create_base_model_class_from_properties(
            model_name=structured_tool.name + "_args_schema",
            properties=properties
        )

        return structured_tool

    @staticmethod
    def create_base_model_class_from_properties(
        model_name: str,
        properties: dict[str, Any]
    ) -> type[BaseModel]:
        """Create a `BaseModel` from ``properties`` in ``args_schema``

        Args:
            model_name: Name of model
            properties:
                ```python
                    {
                        'field': {..., 'type': 'string|integer'}
                    }
                ```

        Returns:
            A new subclass of `BaseModel` with class name is ``model_name``
        """
        field_definitions = dict()
        type2type = {
            'string': str,
            'integer': int,
            'boolean': bool,
            'array': list
        }

        for f_name, f_def in properties.items():
            field_definitions[f_name] = (type2type[f_def['type']])

        return create_model(
            model_name,
            **field_definitions
        )

    def run_langchain_tool(
        self,
        tool: Union[BaseTool, StructuredTool],
        tool_call: ToolCall
    ) -> ToolMessage:
        if not isinstance(tool, (BaseTool, StructuredTool)):
            raise ValueError(f"This function only runs ``BaseTool`` or ``StructuredTool``.")

        return self.run(tool.ainvoke(input=tool_call))

    @check_session
    async def list_tools(self):
        """List available tools on server/client has access

        Returns:
            List of tools
        """
        response = await self.session.list_tools()
        self._tools_dict = {
            tool.name: tool
            for tool in response.tools
        }

        return list(self.tools_dict.values())

    @check_session
    async def list_prompts(self):
        """List available prompts on server/client has access

        Returns:
            List of prompts
        """
        response = await self.session.list_prompts()
        self._prompts_dict = {
            prompt.name: prompt
            for prompt in response.prompts
        }

        return list(self.prompts_dict.values())

    @check_session
    async def list_resources(self):
        """List available resources on server/client has access

        Returns:
            List of resources
        """
        response = await self.session.list_resources()
        resources = response.resources
        # logger.info(f"[CLIENT] - Available RESOURCES: {[resource.name for resource in resources]}")

        return resources

    @check_session
    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] = None
    ) -> CallToolResult:
        """The top wrapper tool call of session

        Args:
            name: Name of tool
            arguments: Arguments feed to tool

        Returns:
            Call tool result with attributes `content` and `structuredContent`
        """
        arguments = arguments or dict()
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
        arguments: dict[str, Any] = None
    ) -> GetPromptResult | str:
        """The top wrapper get prompt of session

        Args:
            name: Name of prompt
            arguments: Arguments feed to prompt func

        Returns:
            message: List of PromptMessage
        """
        arguments = arguments or dict()
        prompt = await self.session.get_prompt(name=name, arguments=arguments)

        return prompt.messages[0].content.text

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server

        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        if self.is_connected:
            logger.warning(f"Have already connected to server!!!")
            return

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

        self.is_connected = True
        logger.info(f"Connected to Server at '{server_script_path}'")

    @check_session
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()
