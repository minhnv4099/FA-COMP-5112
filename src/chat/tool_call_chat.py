#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations

import logging
from typing import (
    Union,
    TYPE_CHECKING,
    Generic,
    Optional,
    Sequence,
    Any,
    Literal
)

from langchain_core.tools import StructuredTool
from typing_extensions import override, overload
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from src.registry import RegisterChat, fetch_registered
from src.typing import (
    StateT,
    OutputT,
    ContextT,
    ToolSchema,
    MappingLike
)
from src.chat.base import BaseChat, LanguageModelInput
from src.chat.mixin import ToolCallChatMixin
from src.types import BaseOutput
from src.message.parsed_tool_call import ParsedTollCallMessage
from src.utils.decorator import must_override, add_note_docstring
from src.mcp.client import MCPClientToolExecutor

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig
    from langchain_core.tools.base import ToolCall, BaseTool
    from langchain_core.messages import (
        ToolMessage,
        BaseMessage,
    )
    from src.typing import SchemaLike

logger = logging.getLogger(__name__)


@RegisterChat(module=__name__, name='tool_call_generate_chat')
class ToolCallGenerateChat(
    ToolCallChatMixin,
    BaseChat,
    Generic[ToolSchema],
    bypass_override=True
):
    """The Chat class can generate tool calls, but not persistent."""

    tool_schemas: list[Union[ToolSchema, dict]]
    """Tool schemas"""

    chat_output: Union[ToolSchema, dict]
    """Output schema"""

    mcp_client: MCPClientToolExecutor
    """MCP Client with tools on MCP Server"""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

    def __init__(
        self,
        *args,
        tool_schemas: list[ToolSchema] = None,
        chat_output: ToolSchema = None,
        mcp_client: Optional[MCPClientToolExecutor] = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.tool_schemas = tool_schemas
        self.chat_output = chat_output
        self.mcp_client = mcp_client

        self._langchain_tools: dict[str, ToolSchema] = dict()
        self._mcp_tools: dict[str, Union[BaseTool, StructuredTool]] = dict()

        if self.llm_engine:
            self.bind_schemas(self._merge_tools())

    @property
    def mcp_tools_as_langchain_tools(self):
        if self.mcp_client is None:
            return dict()
        """Dict of {name: ``BaseTool`` | ``StructuredTool``}"""
        if not self._mcp_tools:
            self._mcp_tools = {
                tool.name: self.mcp_client.mcp_tool_to_langchain_tool(tool)
                for tool in self.mcp_client.tools
            }

        return self._mcp_tools

    @property
    def langchain_tools(self):
        """Dict of {name: ``BaseTool`` | ``ToolSchema``}"""
        if not self._langchain_tools:
            self._langchain_tools = self._validate_schemas()

        return self._langchain_tools

    def _merge_tools(self):
        common_names = set(self.langchain_tools.keys()).intersection(set(self.mcp_tools_as_langchain_tools.keys()))
        if common_names:
            logger.warning(f"Some name conflicts: {common_names}")

        return list(self.langchain_tools.values()) + list(self.mcp_tools_as_langchain_tools.values())

    def get_tool(self, name: str):
        if name in self.langchain_tools:
            return self.langchain_tools[name]

        if name in self.mcp_tools_as_langchain_tools:
            return self.mcp_tools_as_langchain_tools[name]

        raise ValueError(f"No tool name {name!r}") from None

    def _make_system_prompt(self, name: Optional[str] = 'asset_creation_strategy'):
        try:
            system_message = SystemMessage(
                content=self.mcp_client.run(
                    self.mcp_client.get_prompt(name=name)
                )
            )

            return system_message
        except Exception:
            return None

    @override
    def invoke(
        self,
        input: LanguageModelInput,
        config: Optional[Union[RunnableConfig, dict]] = None,
        *,
        stop: Optional[list[str]] = None
    ) -> Union[AIMessage, ParsedTollCallMessage, ToolMessage]:
        """"""
        system_message = self._make_system_prompt(None)
        if system_message:
            input = [
                system_message,
                HumanMessage(content=input)
            ]

        ai_message = super().invoke(
            input=input,
            config=config,
            stop=stop
        )

        if not ai_message.tool_calls:
            return ai_message

        tool_based_messages = [
            self._internal_call_tool(tool_call)
            for tool_call in ai_message.tool_calls
        ]

        # return an AIMessage with all tool calls as content
        if len(tool_based_messages) > 1:
            return self._combine_message(
                *tool_based_messages)

        return tool_based_messages[0]

    @add_note_docstring('Parse tool call to formated output')
    def _internal_call_tool(
        self,
        tool_call: ToolCall,
        **kwargs,
    ) -> ParsedTollCallMessage:
        """The actual handler tool call. This chat class just parses args of tool call into structure output

        Args:
            tool_call: Contains information about the tool

        Returns:
            ParsedTollCallMessage subclass of ToolMessage whose content is args in ``tool_call``
        """
        return ParsedTollCallMessage(
            content=self.get_pretty_prep(tool_call['args']),
            tool_call_id=tool_call['id'],
            name=tool_call['name'],
            raw_content=tool_call['args'],
        )

    def bind_schemas(self, schemas: list[ToolSchema]):
        if schemas:
            logger.info(f"The {self.name!r} has access to {len(schemas)} schemas "
                        f"({len(self.tool_schemas)} langchain tools, "
                        f"{len(self.mcp_client.tools)} mcp tools, "
                        f"{1 if self.chat_output else 0} outputs).")
        tool_choice = None
        if len(schemas) == 1 and issubclass(schemas[0], BaseOutput):
            tool_choice = True

        self.chat_model = self.llm_engine.bind_tools(   # type: ignore
            tools=schemas,
            strict=False,
            tool_choice=tool_choice
        )

    def _validate_schemas(self) -> dict[str, ToolSchema]:
        """Validate output schemas to chat model"""
        self.tool_schemas = self._convert_to_list(seq=self.tool_schemas)
        chat_output = self._convert_to_list(seq=self.chat_output)
        # get all schemas, do matter output schema and tool schema
        # let model know schemas
        schemas = self.fetch_schemas(self.tool_schemas + chat_output)
        schemas = list(filter(lambda x: x, schemas))

        return {
            schema.name: schema
            for schema in schemas
        }

    def fetch_schemas(self, schemas: list[Union[ToolSchema, dict]]) -> list[SchemaLike]:
        return [
            self.fetch_schema(schema=schema)
            for schema in schemas
        ]

    @staticmethod
    def fetch_schema(schema: Union[dict, ToolSchema]) -> Union[None, SchemaLike]:
        if not isinstance(schema, MappingLike):
            return schema

        schema_obj = fetch_registered(metadata=schema)
        # force schema's name and object's name are similar
        schema_obj.name = schema['name']

        return schema_obj


@RegisterChat(module=__name__, name='tool_call_execute_chat')
class ToolCallExecuteChat(
    ToolCallGenerateChat,
    Generic[StateT, ContextT, OutputT, ToolSchema]
):
    """The Chat class can execute tool, but not persistent."""

    def __init_subclass__(cls):
        ...

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.langchain_tools or self.mcp_tools_as_langchain_tools:
            logger.info(f"[TOOL] The {self.name!r} can execute "
                        f"{len(self.langchain_tools)!r} langchain tools and "
                        f"{len(self.mcp_tools_as_langchain_tools)!r} mcp tools")

    @add_note_docstring('Execute tool call')
    @override
    def _internal_call_tool(self, tool_call: ToolCall, **kwargs) -> Union[ToolMessage, ParsedTollCallMessage]:
        """Actually execute the tool call.
        If no tool (function) is found, treat it as tool schema -> parse output.
        """
        try:
            tool = self.get_tool(name=tool_call['name'])
        except ValueError as e:
            raise e

        if self._is_mcp_tool(tool_call):
            logger.info("Call mcp tool")
            # ToolMessage
            return self.mcp_client.run_langchain_tool(tool=tool, tool_call=tool_call)

        if self._is_langchain_tool(tool_call):
            logger.info("Call langchain tool")
            # ToolMessage
            return tool.invoke(input=tool_call)

        # ParsedTollCallMessage
        return super()._internal_call_tool(tool_call=tool_call)

    def _is_mcp_tool(self, tool_call: ToolCall):
        return tool_call['name'] in self.mcp_tools_as_langchain_tools

    def _is_langchain_tool(self, tool_call: ToolCall):
        return tool_call['name'] in self.langchain_tools
