#
#  Copyright (c) 2026
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations

import asyncio
import nest_asyncio

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
from typing_extensions import override, deprecated

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


logger = logging.getLogger("MCP Client")


@runtime_checkable
class MCPClientProtocol(Protocol):

    @property
    @abstractmethod
    def tools_dict(self) -> dict[str, Tool]: ...

    @property
    def tools(self) -> list[Tool]: ...

    @property
    def tool_names(self) -> list[str]: ...

    def get_mcp_tool(self, name: str) -> Tool: ...

    def mcp_tool_to_langchain_tool(self, tool: Tool) -> Union[BaseTool, StructuredTool]: ...

    def run_langchain_tool(
            self,
            tool: Union[BaseTool, StructuredTool],
            tool_call: ToolCall
    ) -> ToolMessage: ...

    @property
    @abstractmethod
    def prompts_dict(self) -> dict[str, Prompt]: ...

    @property
    def prompts(self) -> list[Prompt]: ...

    @property
    def prompt_names(self) -> list[str]: ...

    def get_mcp_prompt(self, name: str) -> str: ...

    def get_prompt(self, name: str) -> GetPromptResult | str: ...

    @property
    @abstractmethod
    def resources_dict(self) -> dict[str, Resource]: ...

    @property
    def resources(self) -> list[Resource]: ...

    @property
    def resource_names(self) -> list[str]: ...

    def get_mcp_resource(self, name: str) -> str: ...

    def read_resource(self, uri: Union[AnyUrl, str]) -> ReadResourceResult | str: ...


class MCPClientMixin(ABC, metaclass=ABCMeta):
    """"""

    @final
    @deprecated("This function is just backup when forcing coro. await coro instead for better operation.")
    def run(self, coro: Coroutine[Any, Any, Any]) -> Any:
        """Run coroutine, used when in sync context."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            # Nếu loop đang chạy (Uvicorn), ta apply nest_asyncio ngay tại đây.
            # Nó sẽ cho phép loop.run_until_complete(coro) hoạt động mà không gây lỗi.
            nest_asyncio.apply()

        return loop.run_until_complete(coro)

    @property
    @abstractmethod
    def tools_dict(self) -> dict[str, Tool]:
        """Dictionary mapping name tool to MCP tool"""

    @property
    def tools(self) -> list[Tool]:
        """List of MCP tools"""
        return list(self.tools_dict.values())

    @property
    def tool_names(self) -> list[str]:
        """List of tool names"""
        return list(self.tools_dict.keys())

    def get_mcp_tool(self, name: str) -> Tool | None:
        """Get an MCP tool by name.
        Return `None` if not found."""
        if name not in self.tool_names:
            logger.info(
                f"No tool name {name!r}."
                f"Available tool names: {self.tool_names}"
            )
            return None

        return self.tools_dict[name]

    @deprecated("This function will be removed. "
                "Use `convert_mcp_tool_to_langchain_tool` from `langchain_mcp_adapters` instead.")
    def mcp_tool_to_langchain_tool(self, tool: Tool) -> Union[BaseTool, StructuredTool]:
        """Convert a mcp tool to langchain tool."""
        structured_tool = convert_mcp_tool_to_langchain_tool(tool=tool, session=self.session)

        return structured_tool

    @deprecated('This function will be removed. Should not run tool manually.')
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
        """List of Prompts"""
        return list(self.prompts_dict.values())

    @property
    def prompt_names(self) -> list[str]:
        """List of prompt names"""
        return list(self.prompts_dict.keys())

    def get_mcp_prompt(self, name: str) -> Prompt | None:
        """Get an MCP prompt"""
        if name not in self.prompt_names:
            logger.info(
                f"No prompt name {name!r}"
                f"Available prompt names: {self.prompt_names!r}"
            )
            return None

        return self.prompts_dict[name]

    @property
    @abstractmethod
    def resources_dict(self) -> dict[str, Resource]:
        """Dictionary mapping name to MCP resources."""

    @property
    def resources(self) -> list[Resource]:
        """List of MCP resources"""
        return list(self.resources_dict.values())

    @property
    def resource_names(self) -> list[str]:
        """List of resource names."""
        return list(self.resources_dict.keys())

    def get_mcp_resource(self, name: str) -> Resource | None:
        if name not in self.prompt_names:
            logger.info(
                f"No prompt name {name!r}"
                f"Available prompt names: {self.prompt_names!r}"
            )
            return None

        return self.resources_dict[name]
