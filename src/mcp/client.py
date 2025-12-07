#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations

import asyncio
import logging
import functools
import os.path
from abc import ABC, ABCMeta, abstractmethod
from typing import (
    Optional,
    Any,
    Union,
    Coroutine,
    final,
    TYPE_CHECKING,
    Protocol,
    runtime_checkable
)
from typing_extensions import override

from langchain_core.tools import BaseTool, StructuredTool
from langchain_mcp_adapters.tools import convert_mcp_tool_to_langchain_tool
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.types import AnyUrl, Tool, Prompt, Resource
from mcp.types import CallToolResult, ReadResourceResult, GetPromptResult
from contextlib import AsyncExitStack

if TYPE_CHECKING:
    from langchain_core.messages import ToolMessage
    from langchain_core.tools.base import ToolCall

logger = logging.getLogger(__name__)


@runtime_checkable
class MCPClientProtocol(Protocol):

    @staticmethod
    @final
    def run(coro: Coroutine[Any, Any, Any]) -> Any: ...

    @property
    @abstractmethod
    def tools_dict(self): ...

    @property
    def tools(self) -> list[Tool]: ...

    @property
    def tool_names(self): ...

    def get_mcp_tool(self, name: str) -> Tool: ...

    def mcp_tool_to_langchain_tool(self, tool: Tool) -> Union[BaseTool, StructuredTool]: ...

    def run_langchain_tool(
        self,
        tool: Union[BaseTool, StructuredTool],
        tool_call: ToolCall
    ) -> ToolMessage: ...

    @property
    @abstractmethod
    def prompts_dict(self): ...

    @property
    def prompts(self) -> list[Tool]: ...

    @property
    def prompt_names(self): ...

    def get_mcp_prompt(self, name: str) -> str: ...

    def get_prompt(self, name: str) -> GetPromptResult | str: ...

    @property
    @abstractmethod
    def resources_dict(self): ...

    @property
    def resources(self) -> list[Tool]: ...

    @property
    def resource_names(self): ...

    def get_mcp_resource(self, name: str) -> str: ...

    def read_resource(self, uri: Union[AnyUrl, str]) -> ReadResourceResult | str: ...


class MCPClientMixin(ABC, metaclass=ABCMeta):
    """"""

    @staticmethod
    @final
    def run(coro: Coroutine[Any, Any, Any]) -> Any:
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = asyncio.get_event_loop()

        return current_loop.run_until_complete(coro)

    @property
    @abstractmethod
    def tools_dict(self) -> dict[str, Tool]:
        """Dictionary mapping name tool to tool"""

    @property
    def tools(self) -> list[Tool]:
        """List of tools"""
        return list(self.tools_dict.values())

    @property
    def tool_names(self) -> list[str]:
        """List of tool names"""
        return list(self.tools_dict.keys())

    def get_mcp_tool(self, name: str) -> Tool:
        """Get a MCP tool"""
        if name not in self.tool_names:
            logger.info(f"Available tool names: {self.tool_names}")
            raise ValueError(f"No tool name {name!r}") from None

        return self.tools_dict[name]

    def mcp_tool_to_langchain_tool(self, tool: Tool) -> Union[BaseTool, StructuredTool]:
        """Convert a mcp tool to langchain tool. Also change ``args_schema`` from `dict` to `BaseModel`"""
        structured_tool = convert_mcp_tool_to_langchain_tool(tool=tool, session=self.session)

        return structured_tool

    def run_langchain_tool(
        self,
        tool: Union[StructuredTool],
        tool_call: ToolCall
    ) -> ToolMessage:
        if not isinstance(tool, (BaseTool, StructuredTool)):
            raise ValueError(f"This function only runs ``BaseTool`` or ``StructuredTool``.")

        return self.run(tool.ainvoke(input=tool_call))

    @property
    @abstractmethod
    def prompts_dict(self) -> dict[str, Prompt]:
        """Dictionary mapping name to prompt."""

    @property
    def prompts(self) -> list[Prompt]:
        """A list of Prompts"""
        return list(self.prompts_dict.values())

    @property
    def prompt_names(self) -> list[str]:
        """A list of prompt names"""
        return list(self.prompts_dict.keys())

    def get_mcp_prompt(self, name: str) -> Prompt:
        """Get a MCP prompt"""
        if name not in self.prompt_names:
            logger.info(f"Available prompt names: {self.prompt_names!r}")
            raise ValueError(f"No prompt name {name!r}") from None

        return self.prompts_dict[name]

    @property
    @abstractmethod
    def resources_dict(self) -> dict[str, Resource]:
        """Dictionary mapping name to resource."""

    @property
    def resources(self) -> list[Resource]:
        """List of resources"""
        return list(self.resources_dict.values())

    @property
    def resource_names(self) -> list[str]:
        """List of resource names."""
        return list(self.resources_dict.keys())

    def get_mcp_resource(self, name: str) -> Resource:
        if name not in self.prompt_names:
            logger.info(f"Available prompt names: {self.prompt_names!r}")
            raise ValueError(f"No prompt name {name!r}") from None

        return self.resources_dict[name]


class SingleServerMCPClient(MCPClientMixin):

    session: Optional[ClientSession]
    """Session"""

    exit_stack: Optional[AsyncExitStack]
    """Stack exitter"""

    server_script_path: str
    """Path to script server"""

    name: str
    """Name of client. Typically used to distinguish clients in multiple servers"""

    _tools_dict: dict[str, Tool] = dict()
    """{name: Tool}"""

    _prompts_dict: dict[str, Prompt] = dict()
    """{name: Prompt}"""

    _resources_dict: dict[str, Resource] = dict()
    """{name: Resource}"""

    def __init__(
        self,
        name: str = None,
        server_script_path: Optional[str] = None,
        *,
        exit_stack: Optional[AsyncExitStack] = None,
        **kwargs,
    ):
        self.name = name or server_script_path.split('/')[-1].split('.')[0]
        self.exit_stack = exit_stack or AsyncExitStack()
        self.session = None

        self.server_script_path = server_script_path
        self.run(self.connect_to_server(server_script_path))

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
        if not self._tools_dict:
            self._tools_dict = self.run(self._list_tools())

        return self._tools_dict

    @property
    @override
    def prompts_dict(self):
        """Dict of {name: Prompt}"""
        if not self._prompts_dict:
            self._prompts_dict = self.run(self._list_prompts())

        return self._prompts_dict

    @property
    @override
    def resources_dict(self) -> dict[str, Resource]:
        if not self._resources_dict:
            self._resources_dict = self.run(self._list_resources())

        return self._resources_dict

    @check_session
    async def _list_tools(self):
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
    async def _list_prompts(self):
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
    async def _list_resources(self):
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
    def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] = None,
        return_raw: bool = False
    ) -> CallToolResult | dict:
        """The top wrapper tool call of session

        Args:
            name: Name of tool
            arguments: Arguments feed to tool
            return_raw: Return raw Tool result or structuredContent.

        Returns:
            Call tool result with attributes `content` and `structuredContent`
        """
        arguments = arguments or dict()
        tool_result: CallToolResult = self.run(self.session.call_tool(name=name, arguments=arguments))

        if return_raw:
            return tool_result
        return tool_result.structuredContent

    @check_session
    def get_prompt(
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
        prompt_result: GetPromptResult = self.run(self.session.get_prompt(name=name, arguments=arguments))
        logger.info(f"Get system prompt {name!r}")
        if return_raw:
            return prompt_result
        return prompt_result.messages[0].content.text

    @check_session
    def read_resource(
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
        resource_result: ReadResourceResult = self.run(self.session.read_resource(uri))

        if return_raw:
            return resource_result
        return resource_result.contents[0].text

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server

        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        if self.session:
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

        logger.info(f"Connected to {self.name!r} Server at {server_script_path!r}")

    @check_session
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


class MultiServerMCPClient(MCPClientMixin):
    """MCP client with multiple servers

    Args:
        server_script_paths: A tuple of:

            * Two-element tuple: first is name of that server, second is path to server ``.py`` file. Now we only support ``.py`` file.
            For example::

                [('name', 'server_file'), ...]
            * Server file: List server paths, in this case name of server is server file name (without extension).
            For example::

                ['server_file' ...]
            * Mixed elements.
            For example::

                [('name', 'server_file'), 'server_file', ...]

    """
    server_script_paths: list[str | tuple]
    """List of server path (and displayed name client)"""

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

    def __init__(self, server_script_path: list[str | tuple]):
        self.server_script_paths = server_script_path

        for tup in server_script_path:
            if isinstance(tup, tuple):
                if len(tup) == 2:
                    mcp_client = SingleServerMCPClient(server_script_path=tup[1], name=tup[0])
                if len(tup) == 1:
                    mcp_client = SingleServerMCPClient(server_script_path=tup[0])
            elif isinstance(tup, str):
                mcp_client = SingleServerMCPClient(server_script_path=tup)

            self.mcp_clients[mcp_client.name] = mcp_client

    @property
    def tools_dict(self):
        if not self._tools_dict:
            for client_name, client in self.mcp_clients.items():
                for tool_name, tool in client.tools_dict.items():
                    # prompt name exposed to llm
                    _name = client_name + self._separator_client_vs_comp_name + tool_name
                    tool.name = _name
                    self._tools_dict[_name] = tool

        return self._tools_dict

    @property
    def prompts_dict(self):
        if not self._prompts_dict:
            for client_name, client in self.mcp_clients.items():
                for prompt_name, prompt in client.prompts_dict.items():
                    # prompt name exposed to llm
                    _name = client_name + self._separator_client_vs_comp_name + prompt_name
                    prompt.name = _name
                    self._prompts_dict[_name] = prompt

        return self._prompts_dict

    @property
    def resources_dict(self):
        if not self._resources_dict:
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
            logger.info(f"Invalid prompt name {name!r}. Available: {self.prompt_names}")
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
            logger.info(f"Invalid resource uri {uri!r}. Available: {self.resource_names}")
            return None

        client_name, original_resource_uri = resource_name.split(self._separator_client_vs_comp_name)
        client = self.mcp_clients[client_name]

        return client.read_resource(uri=original_resource_uri)

    @override
    def mcp_tool_to_langchain_tool(self, tool: Tool) -> Union[BaseTool, StructuredTool]:
        """Convert mcp tool to langchain tool. Its name is combined as client name + tool name"""
        # split exposed tool name to get client and original tool name
        client_name, tool_name = tool.name.split(self._separator_client_vs_comp_name)
        client = self.mcp_clients[client_name]

        # conver combine-name tool
        langchain_tool = client.mcp_tool_to_langchain_tool(tool)

        # Note: after getting langchain tool with combined name, MUST set mcp tool original name.
        tool.name = tool_name

        return langchain_tool
