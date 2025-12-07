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
from src.typing import ToolSchema, MappingLike

from src.chat.base import BaseChat, LanguageModelInput
from src.chat.mixin import ToolCallChatMixin
from src.message.parsed_tool_call import ParsedTollCallMessage
from src.utils.decorator import add_note_docstring
from src.mcp.client import MCPClientProtocol

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig
    from langchain_core.tools.base import ToolCall, BaseTool
    from langchain_core.messages import ToolMessage
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

    _schemas: dict[str, ToolSchema] = dict()
    """Schemas to bind"""

    _langchain_tools: dict[str, ToolSchema] = dict()
    """Langchain tools"""

    _mcp_tools: dict[str, Union[BaseTool, StructuredTool]] = dict()
    """MCP tools"""

    mcp_client: Optional[MCPClientProtocol]
    """MCP Client with tools on MCP Server"""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

    def __init__(
        self,
        *args,
        schemas: Union[dict[str, ToolSchema], list[ToolSchema], list[dict[str, str]]] = None,
        mcp_client: Optional[MCPClientProtocol] = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self._schemas = self._validate_schemas(schemas)
        self.mcp_client = mcp_client

        if self.llm_engine:
            schemas = list(self.schemas.values()) + list(self.mcp_tools_as_langchain_tools.values())
            self._merge_tools()
            self.bind_schemas(schemas)

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
            self._langchain_tools = {
                schema_name: schema
                for schema_name, schema in self.schemas.items()
                if schema.type == 'tool'
            }

        return self._langchain_tools

    @property
    def schemas(self):
        if not self._schemas:
            self._schemas = self._validate_schemas(None)

        return self._schemas

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

        raise ValueError(f"No tool name {name!r}.")

    # TODO: change name of method
    def _dynamic_input(self, input: LanguageModelInput, name: Optional[str] = "general_system_prompt"):
        has_system_prompt = isinstance(input, list) and list(filter(lambda m: isinstance(m, SystemMessage), input))
        if not has_system_prompt:
            system_message = self._get_system_prompt(name=name)
            if system_message:
                if isinstance(input, str):
                    hu_me = HumanMessage(content=input)
                elif isinstance(input, HumanMessage):
                    hu_me = input

                return [
                    system_message,
                    hu_me
                ]

        return input

    def _get_system_prompt(self, name: Optional[str] = 'general_system_prompt'):
        try:
            system_message = SystemMessage(
                content=self.mcp_client.get_prompt(name)
            )

            return system_message
        except Exception as e:
            logger.error(f"Error getting system prompt: {str(e)}")
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
        input = self._dynamic_input(input)
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
            logger.info(f"The {self.name!r} has access to {len(schemas)} schemas: "
                        f"({len(self.schemas)} (langchain), "
                        f"{len(self.mcp_client.tools)} (mcp)).")
        tool_choice = None
        if len(schemas) == 1 and schemas[0].type == 'chat_output':
            tool_choice = True

        self.chat_model = self.llm_engine.bind_tools(   # type: ignore
            tools=schemas,
            strict=False,
            tool_choice=tool_choice
        )

    @overload
    def _validate_schemas(self, schemas) -> dict[str, ToolSchema]: ...

    def _validate_schemas(
        self,
        schemas: Union[
            dict[str, ToolSchema],
            list[ToolSchema],
            list[dict[str, str]]
        ] = None
    ) -> dict[str, ToolSchema]:
        schemas = schemas or self._schemas
        if not schemas:
            return dict()

        if isinstance(schemas, dict):
            # Likely is {name: ToolSchema}
            schema_objs = schemas
        elif isinstance(schemas, list):
            schema_objs = self.fetch_schemas(schemas)
        else:
            logger.error(f"Expect {type[list]!r} or {type[dict]!r}, but got {type(schemas)!r}")
            schema_objs = []

        schemas = list(filter(lambda x: x, schema_objs))

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
        try:
            if not isinstance(schema, MappingLike):
                raise NotImplemented(f"Now we don't support pre-defined schema ({type(schema)!r})"
                                     f". Only creating from dict. So treat as None")
                schema_obj = schema
                # TODO: solve this
                schema_obj.type = schema.__getattribute__('type')
            else:
                schema_obj = fetch_registered(metadata=schema)
                schema_obj.type = schema['type']

            try:
                schema_obj.name = schema_obj.name
            except AttributeError:
                schema_obj.name = schema_obj.__name__
        except NotImplemented as e:
            logger.critical(str(e))
            return None

        return schema_obj


@RegisterChat(module=__name__, name='tool_call_execute_chat')
class ToolCallExecuteChat(ToolCallGenerateChat):
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
            if self._is_mcp_tool_call(tool_call):
                logger.info(f"Call mcp tool {tool.name!r}")
                # ToolMessage
                return self.mcp_client.run_langchain_tool(tool=tool, tool_call=tool_call)

            if self._is_langchain_tool_call(tool_call):
                logger.info(f"Call langchain tool {tool.name!r}")
                # ToolMessage
                return tool.invoke(input=tool_call)
            # ParsedTollCallMessage
            return super()._internal_call_tool(tool_call=tool_call)
        except ValueError as e:
            logger.info("%s %s", e, 'Return as tool call.')
            # ParsedTollCallMessage
            return super()._internal_call_tool(tool_call=tool_call)

    def _is_mcp_tool_call(self, tool_call: ToolCall):
        return tool_call['name'] in self.mcp_tools_as_langchain_tools

    def _is_langchain_tool_call(self, tool_call: ToolCall):
        return tool_call['name'] in self.langchain_tools

    def _is_structured_output(self, tool_call: ToolCall):
        if self._is_mcp_tool_call(tool_call) or self._is_langchain_tool_call(tool_call):
            return False

        return self.schemas[tool_call['name']].type == "chat_output"
