#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
"""The chat inheriting persistent chat with ability parse structured output as dict
Example:
    {
        "results": <RESULT>,
        "command": <BASH COMMAND>
    }
"""

from __future__ import annotations

import logging
from typing import (
    Union,
    TYPE_CHECKING,
    Generic,
    Optional,
    Sequence,
    Any
)
from typing_extensions import override
from langchain_core.messages import AIMessage

from src.registry import RegisterChat, fetch_registered, load_tool
from src.types import (
    StateT,
    OutputT,
    ContextT,
    ToolSchema,
    MappingLike
)
from src.chat.base import BaseChat, LanguageModelInput
from src.chat.mixin import ToolCallChatMixin
from src.chat_output.comp_5112 import BaseOutput
from src.message.parsed_tool_call import ParsedTollCallMessage
from src.utils.decorator import must_override, add_note_docstring
from src.utils.exception import NotFoundTool

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig
    from langchain_core.tools.base import ToolCall
    from langchain_core.messages import (
        ToolMessage,
        BaseMessage,
    )
    from src.types import SchemaLike
    from src.tool.base import BaseDefinedTool

logger = logging.getLogger(__name__)


@RegisterChat(module_path=__name__, name='tool_call_generate_chat')
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

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

    def __init__(
        self,
        *args,
        tool_schemas: list[Union[ToolSchema, dict]] = None,
        chat_output: Union[ToolSchema, dict] = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.tool_schemas = tool_schemas
        self.chat_output = chat_output
        # bind schemas to the llm engine
        if self.llm_engine:
            schemas = self._validate_schemas()
            self.bind_schemas(schemas)

    @override
    def invoke(
        self,
        input: LanguageModelInput,
        config: Optional[Union[RunnableConfig, dict]] = None,
        *,
        stop: Optional[list[str]] = None
    ) -> Union[AIMessage, ParsedTollCallMessage]:
        """"""
        ai_message = super().invoke(
            input=input,
            config=config,
            stop=stop
        )

        if not ai_message.tool_calls:
            return ai_message

        tool_based_messages = [
            self._internal_tool_call(tool_call)
            for tool_call in ai_message.tool_calls
        ]

        # return an AIMessage with all tool calls as content
        if len(tool_based_messages) > 1:
            return self._combine_message(
                *tool_based_messages)

        return tool_based_messages[0]

    @add_note_docstring('Parse tool call to formated output')
    def _internal_tool_call(
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

    @must_override
    def _validate_schemas(self) -> list[ToolSchema]:
        """Validate output schemas to chat model"""
        self.tool_schemas = self._convert_to_list(seq=self.tool_schemas)
        self.chat_output = self._convert_to_list(seq=self.chat_output)
        # get all schemas, do matter output schema and tool schema
        # let model know schemas
        schemas = self.fetch_schemas(self.tool_schemas + self.chat_output)
        schemas = list(filter(lambda x: x, schemas))
        if schemas:
            logger.info(f"The {self.name!r} has access to {len(schemas)} schemas"
                        f" ({len(self.tool_schemas)} tool(s) + {len(self.chat_output)} outputs).")

        return schemas

    def bind_schemas(self, schemas: list[ToolSchema]):
        tool_choice = 'any'
        if len(schemas) == 1 and issubclass(schemas[0], BaseOutput):
            tool_choice = True

        self.chat_model = self.llm_engine.bind_tools(   # type: ignore
            tools=schemas,
            strict=True,
            tool_choice=tool_choice,
        )

    def fetch_schemas(self, schemas: list[Union[ToolSchema, dict]]) -> list[SchemaLike]:
        return [
            self.fetch_schema(schema=schema)
            for schema in schemas
        ]

    def fetch_schema(self, schema: Union[dict, ToolSchema]) -> Union[None, SchemaLike]:
        if not isinstance(schema, MappingLike):
            return schema

        schema_obj = fetch_registered(metadata=schema)
        # make sure schema's name and object's name are similar
        schema_obj.name = schema['name']

        return schema_obj


@RegisterChat(module_path=__name__, name='tool_call_execute_chat')
class ToolCallExecuteChat(
    ToolCallGenerateChat,
    Generic[StateT, ContextT, OutputT, ToolSchema]
):
    """The Chat class can execute tool, but not persistent."""

    def __init_subclass__(cls):
        ...

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.tools = get_tools_from_schemas(self.tool_schemas)
        if self.tools:
            logger.info(f"The {self.name!r} can execute {len(self.tools)} tools.")

    @add_note_docstring('Execute tool call')
    @override
    def _internal_tool_call(
        self,
        tool_call: ToolCall,
        **kwargs
    ) -> Union[ToolMessage, ParsedTollCallMessage]:
        """Actually execute the tool call.
        If no tool (function) is found, treat it as tool schema -> parse output.
        """
        if tool_call['name'] in self.tools:
            tool = self.tools[tool_call['name']]
            # ToolMessage
            return tool.invoke(input=tool_call)
        else:
            # ParsedTollCallMessage
            return super()._internal_tool_call(tool_call=tool_call)


def get_tools_from_schemas(tool_schemas: Sequence[Union[ToolSchema, dict]]) -> dict[str, BaseDefinedTool]:
    executable_tools = dict()
    for schema in tool_schemas:
        if schema['type'] == 'tool':
            try:
                executable_tools[schema['name']] = load_tool(
                    name=schema['name'],
                    **schema.get('tool_kwargs', dict())
                )
            except NotFoundTool as e:
                continue

    return executable_tools
