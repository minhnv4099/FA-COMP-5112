#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations

import asyncio
import copy
import logging
import functools
import os.path
import warnings
from abc import ABC, ABCMeta, abstractmethod
from typing import (
    Optional,
    Any,
    Union,
    Coroutine,
    final,
    TYPE_CHECKING,
    Protocol,
    runtime_checkable,
    cast
)

from sympy.codegen.fnodes import use_rename
from typing_extensions import override

from langchain_core.tools import BaseTool, StructuredTool
from langchain_mcp_adapters.tools import (
    convert_mcp_tool_to_langchain_tool,
    load_mcp_tools,
    create_session
)
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.types import AnyUrl, Tool, Prompt, Resource
from mcp.types import CallToolResult, ReadResourceResult, GetPromptResult
from contextlib import AsyncExitStack, suppress

from src.mcp.client.mixin import MCPClientMixin


if TYPE_CHECKING:
    from langchain_core.messages import ToolMessage
    from langchain_core.tools.base import ToolCall

logger = logging.getLogger(__name__)
DEFAULT_LOCALHOST = 'http://localhost'
DEFAULT_TRANSPORT = 'sse'


class SingleServerMCPClient(MCPClientMixin):

    session: Optional[ClientSession]
    """Session"""

    exit_stack: Optional[AsyncExitStack]
    """Stack exitter"""

    server_script_path: str
    """Path to script server"""

    name: str
    """Name of client. Typically used to distinguish clients in multiple servers"""

    _tools_dict: dict[str, Tool] = None
    """{name: Tool}"""

    _prompts_dict: dict[str, Prompt] = None
    """{name: Prompt}"""

    _resources_dict: dict[str, Resource] = None
    """{name: Resource}"""

    def __init__(
        self,
        name: Optional[str] = None,
        endpoint: Optional[str | int] = None,
        **kwargs,
    ):
        """MCP Client connecting to a single server.

        Args:
            name: Name of the client.
            endpoint:
                Endpoint of server to connect.
                It can be path to python file for `stdio` transport.
                `Url` or `port` for `sse` transport.
        """
        self.name = name or endpoint
        self.endpoint = endpoint

        self.exit_stack = AsyncExitStack()
        self.session = None

    @classmethod
    def create_client(cls, endpoint: str | int, name: str = None) -> SingleServerMCPClient | None:
        """Create a client based on endpoint.

        If endpoint is a path to a python file, return `obj:[SingleStdioServerMCPClient]`. \n
        If endpoint is a url or port number, return `obj:[SingleSseServerMCPClient]`.
        """
        if name is None:
            name = endpoint

        if isinstance(endpoint, str) and endpoint.endswith('.py'):
            return SingleStdioServerMCPClient(name, endpoint)

        if isinstance(endpoint, str):
            return SingleSseServerMCPClient(name, endpoint)

        if isinstance(endpoint, int):
            endpoint = f"{DEFAULT_LOCALHOST}:{endpoint}/{DEFAULT_TRANSPORT}"
            return SingleSseServerMCPClient(name, endpoint)

        return None

    async def __aenter__(self):
        await self.aconnect_to_server()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()

    @staticmethod
    def check_session(func: callable):
        @functools.wraps(func)
        def wrapped_func(self, *args, **kwargs):
            if self.session is None:
                raise ValueError(f"The session is now None, call 'connect_to_server' to connect to server before calling {func.__name__!r}")
            return func(self, *args, **kwargs)

        return wrapped_func

    @property
    @override
    def tools_dict(self):
        """Dict of {name: Tool}"""
        if self._tools_dict is None:
            warnings.warn(
                "'tools_dict' is lazy, and it is None. "
                "Call 'self.list_tools' first, then you can access 'tools_dict'. "
            )

        return self._tools_dict

    @property
    @override
    def prompts_dict(self):
        """Dict of {name: Prompt}"""
        if self._prompts_dict is None:
            warnings.warn(
                "'prompts_dict' is lazy, and it is empty. "
                "Call 'self.list_prompts' first, then you can access 'prompts_dict'. "
            )
            # self._prompts_dict = self.run(self.list_prompts())
        return self._prompts_dict

    @property
    @override
    def resources_dict(self) -> dict[str, Resource]:
        if self._resources_dict is None:
            warnings.warn(
                "'resources_dict' is lazy, and it is empty. "
                "Call 'self.list_resources' first, then you can access 'resources_dict'. "
            )
        return self._resources_dict

    @check_session
    async def list_tools(self):
        """List available tools on server/client has access

        Returns:
            Mapping of tools
        """
        response = await self.session.list_tools()
        self._tools_dict = {
            tool.name: tool
            for tool in response.tools
        }

        return self._tools_dict

    @check_session
    async def list_prompts(self):
        """List available prompts on server/client has access

        Returns:
            Mapping of prompts
        """
        response = await self.session.list_prompts()
        self._prompts_dict = {
            prompt.name: prompt
            for prompt in response.prompts
        }

        return self._prompts_dict

    @check_session
    async def list_resources(self):
        """List available resources on server/client has access

        Returns:
            Mapping of resources
        """
        response = await self.session.list_resources()
        self._resources_dict = {
            resource.uri.__repr__(): resource
            for resource in response.resources
        }

        return self._resources_dict

    @check_session
    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] = None,
        return_raw: bool = False
    ) -> CallToolResult | dict:
        """Call MCP tool

        Args:
            name: Name of tool
            arguments: Arguments feed to tool
            return_raw: Return raw Tool result or structuredContent.

        Returns:
            Call tool result with attributes `content` and `structuredContent`
        """
        arguments = arguments or dict()
        tool_result: CallToolResult = await self.session.call_tool(name=name, arguments=arguments)

        if return_raw:
            return tool_result
        return tool_result.structuredContent

    @check_session
    async def get_prompt(
        self,
        name: str,
        arguments: dict[str, Any] = None,
        return_raw: bool = False
    ) -> GetPromptResult | str:
        """The top wrapper get prompt of session

        Args:
            name: Name of prompt
            arguments: Arguments feed to prompt func
            return_raw: Return raw Prompt or text of content.

        Returns:
            message: List of PromptMessage
        """
        arguments = arguments or dict()
        prompt_result: GetPromptResult = await self.session.get_prompt(name=name, arguments=arguments)

        if return_raw:
            return prompt_result
        return prompt_result.messages[0].content.text

    @check_session
    async def read_resource(
        self,
        uri: Union[str, AnyUrl],
        return_raw: bool = False
    ) -> ReadResourceResult | str:
        """The top wrapper read resource of session

        Args:
            uri: Uri to resource (resource://...)
            return_raw: Return raw Resource or only text.

        Returns:
            Including contents - list of TextResourceContents
        """
        if isinstance(uri, str):
            uri = AnyUrl(url=uri)
        resource_result: ReadResourceResult = await self.session.read_resource(uri)

        if return_raw:
            return resource_result
        return resource_result.contents[0].text

    @abstractmethod
    async def make_server_parameters(self, *args):
        """Make and return server parameters based on server type
        `stdio` or `sse`."""

    def connect_to_server(self, *args):
        self.run(self.aconnect_to_server(*args))

    async def aconnect_to_server(self, endpoint: Optional[str] = None):
        """Connect to an MCP server."""
        if self.session:
            logger.warning(f"Have already connected to server!!!")
            return True

        endpoint = endpoint or self.endpoint

        with suppress(BaseException):
            read_stream, write_stream = await self.make_server_parameters(endpoint)
            self.session = await self.exit_stack.enter_async_context(ClientSession(read_stream, write_stream))
            await self.session.initialize()
            return True

        return False

    @check_session
    async def cleanup(self):
        try:
            self.session = None
            if self.exit_stack:
                await self.exit_stack.aclose()
        except RuntimeError as e:
            # logger.warning(f"Client {self.name} cleanup encountered task mismatch: {e}")
            pass
        except Exception as e:
            logger.error(f"Error cleaning up client {self.name}: {e}")


class SingleStdioServerMCPClient(SingleServerMCPClient):

    async def make_server_parameters(self, server_script_path: str):
        assert os.path.isfile(server_script_path)

        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')

        if is_js:
            warnings.warn("Now we only support python file.")

        if not is_python:
            raise ValueError("Server script must be a .py or .js file")

        server_params = StdioServerParameters(
            command='uv',
            args=['run', server_script_path],
            env=None
        )

        transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        read_stream, write_stream = transport

        logger.info(f"{self.name!r} connected to MCP Server at path {server_script_path!r}.")
        return read_stream, write_stream


class SingleSseServerMCPClient(SingleServerMCPClient):

    async def make_server_parameters(self, url: str):
        transport = await self.exit_stack.enter_async_context(sse_client(url))
        read_stream, write_stream = transport

        logger.info(f"{self.name!r} connected to MCP Server at url {url!r}.")
        return read_stream, write_stream


class MultiServerMCPClient(MCPClientMixin):
    """MCP client with multiple servers

    Args:
        connect_params: A tuple of:

            * Two-element tuple: first is name of that server, second is path to server ``.py`` file.
            Now we only support ``.py`` file.
            For example::

                [('name', 'server_file'), ...]
            * Server file: List server paths, in this case name of server is server file name (without extension).
            For example::

                ['server_file' ...]

            * Url or port: 'http://localhost:8000/sse' or '8000'

            * Mixed elements.
            For example::

                [('name', '*.py'), '*.py', 'url', port]

    """
    connect_params: list[str | tuple]
    """Connection parameters"""

    mcp_clients: dict[str, SingleServerMCPClient] = dict()
    """Mapping clients based on their name"""

    _tools_dict: dict[str, Tool] = dict()
    """Mapping name to tool"""

    _prompts_dict: dict[str, Prompt] = dict()
    """Mapping name to prompt"""

    _resources_dict: dict[str, Resource] = dict()
    """Mapping name to resource"""

    _separator_client_vs_comp_name: str = '--'
    """Symbols used for combine client name and component name."""

    def __init__(self, connect_params: list[str | tuple]):
        self.connect_params = connect_params
        self.mcp_clients: dict[str, SingleServerMCPClient] = {}
        self._tools_dict: dict[str, Tool] | None = None
        self._is_connected = False

        for tup in connect_params:
            if isinstance(tup, tuple):
                if len(tup) == 2:
                    name, endpoint = tup[0], tup[1]
                else:  # len(tup) == 1:
                    name, endpoint = None, tup[0]
            else:  # str or int:
                name, endpoint = None, tup

            mcp_client = SingleServerMCPClient.create_client(
                name=name,
                endpoint=endpoint)

            if mcp_client:
                self.mcp_clients[mcp_client.name] = mcp_client

    @property
    def mcp_sessions(self):
        sessions = [
            mcp_client.session
            for mcp_client in self.mcp_clients.values()
        ]

        return sessions

    @property
    def tools_dict(self):
        if self._tools_dict is not None:
            return self._tools_dict

        self._tools_dict = {}
        for client_name, client in self.mcp_clients.items():
            for tool_name, tool in client.tools_dict.items():
                # tool names exposed to llm
                _name = client_name + self._separator_client_vs_comp_name + tool_name
                tool.name = _name
                self._tools_dict[_name] = tool

        return self._tools_dict

    @property
    def prompts_dict(self):
        if self._prompts_dict is not None:
            return self._prompts_dict

        self._prompts_dict = {}
        for client_name, client in self.mcp_clients.items():
            for prompt_name, prompt in client.prompts_dict.items():
                # prompt name exposed to llm
                _name = client_name + self._separator_client_vs_comp_name + prompt_name
                prompt.name = _name
                self._prompts_dict[_name] = prompt

        return self._prompts_dict

    @property
    def resources_dict(self):
        if self._resources_dict is not None:
            return self._resources_dict

        self._resources_dict = {}
        for client_name, client in self.mcp_clients.items():
            for resource_name, resource in client.resources_dict.items():
                # resource name exposed to llm
                _name = client_name + self._separator_client_vs_comp_name + resource_name
                resource.name = _name
                self._resources_dict[_name] = resource

        return self._resources_dict

    def get_prompt(
        self,
        name: str,
        arguments: dict[str, Any] = None
    ) -> GetPromptResult | str | None:
        for prompt_name in self.prompt_names:
            if name in prompt_name or name == prompt_name:
                logger.info(f"Get system prompt {prompt_name!r}")
                break
        else:
            logger.info(f"Invalid prompt name {name!r}. "
                        f"Available: {self.prompt_names}")
            return None

        client_name, original_prompt_name = prompt_name.split(self._separator_client_vs_comp_name)
        client = self.mcp_clients[client_name]
        arguments = arguments or dict()

        return client.get_prompt(name=original_prompt_name, arguments=arguments)

    def read_resource(
        self,
        uri: Union[str, AnyUrl],
    ) -> GetPromptResult | str | None:
        for resource_name in self.resource_names:
            if uri in resource_name or uri == resource_name:
                logger.info(f"Read resource {resource_name!r}")
                break
        else:
            logger.info(f"Invalid resource uri {uri!r}."
                        f" Available: {self.resource_names}")
            return None

        client_name, original_resource_uri = resource_name.split(self._separator_client_vs_comp_name)
        client = self.mcp_clients[client_name]

        return client.read_resource(uri=original_resource_uri)

    @override
    def mcp_tool_to_langchain_tool(self, tool: Tool) -> Union[BaseTool, StructuredTool]:
        """Convert mcp tool to langchain tool. Its name is combined as client name and tool name."""
        # split exposed tool name to get client and original tool names
        client_name, tool_name = tool.name.split(self._separator_client_vs_comp_name)
        client = self.mcp_clients[client_name]

        # convert combine-name tool
        langchain_tool = client.mcp_tool_to_langchain_tool(tool)

        # Note: after getting langchain tool with combined name, MUST set mcp tool original name.
        tool.name = tool_name

        return langchain_tool

    async def aconnect_all(self):
        """Connect mcp clients to server"""
        if not self.mcp_clients or self._is_connected:
            return

        mcp_connections = [
            mcp_client.aconnect_to_server()
            for mcp_client in self.mcp_clients.values()
        ]
        mcp_clients_keep = copy.copy(self.mcp_clients)

        connections = await asyncio.gather(*mcp_connections)
        for conn, mcp_key in zip(connections, self.mcp_clients):
            if not conn:
                mcp_clients_keep.pop(mcp_key)

        self.mcp_clients = mcp_clients_keep
        self._is_connected = True

    async def aprepare_tools(self):
        if self._tools_dict is not None:
            return self._tools_dict

        self._tools_dict = {}
        for client_name, client in self.mcp_clients.items():
            _tool_dict = await client.list_tools()
            for tool_name, tool in _tool_dict.items():
                # tool names exposed to llm
                _name = client_name + self._separator_client_vs_comp_name + tool_name
                tool.name = _name
                self._tools_dict[_name] = tool

        return self._tools_dict

    async def __aenter__(self):
        await self.aconnect_all()
        await self.aprepare_tools()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        logger.info("Automatically cleaning up MCP resources...")
        await self.cleanup()

    async def cleanup(self):
        """Clean up all clients safely"""
        logger.info("MultiServerMCPClient: Starting parallel cleanup...")
        if not self.mcp_clients:
            return

        cleanup_tasks = [client.cleanup() for client in self.mcp_clients.values()]
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

        self.mcp_clients.clear()
        self._tools_dict.clear()
        logger.info("MultiServerMCPClient: Cleanup finished.")
