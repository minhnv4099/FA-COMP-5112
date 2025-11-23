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
    OmegaDict
)
from src.chat.base import BaseChat, LanguageModelInput
from src.chat.mixin import ToolCallChatMixin
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

    chat_output: list[Union[ToolSchema, dict]]
    """Output schema"""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

    def __init__(
        self,
        *args,
        tool_schemas: list[Union[ToolSchema, dict]] = None,
        chat_output: list[Union[ToolSchema, dict]] = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.tool_schemas = tool_schemas
        self.chat_output = chat_output
        # bind schemas to the chat model
        if self.chat_model:
            schemas = self._validate_schemas()
            self.chat_model = self.chat_model.bind_tools(
                tools=schemas,
                strict=True,
                tool_choice='any'
            )

    @override
    def invoke(
        self,
        input: LanguageModelInput,
        config: Optional[Union[RunnableConfig, dict]] = None,
        *,
        stop: Optional[list[str]] = None
    ) -> AIMessage:
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

        return self._combine_message(
            *tool_based_messages)

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
        schemas = [
            self.fetch_schema(schema=schema)
            for schema in self.tool_schemas + self.chat_output
        ]
        schemas = list(filter(lambda x: x, schemas))
        if schemas:
            # logger.warning(f"The schemas '{schemas}' are just (or treated as) tool schemas, which requires "
            #                f"'ToolMessage' after 'AIMessage' that have tool calls with associative tool_call_id.")
            logger.info(f"The '{self.name}' has access to {len(schemas)} schemas"
                        f" ({len(self.tool_schemas)} tools + {len(self.chat_output)} outputs).")
            ...

        return schemas

    def fetch_schema(
        self,
        schema: Union[dict, ToolSchema]
    ) -> Union[None, ToolSchema]:
        if not isinstance(schema, OmegaDict):
            return schema

        schema_obj = fetch_registered(metadata=schema)
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

        self.tools = self._get_tool_from_schemas(self.tool_schemas)

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
            # ToolMessage
            tool = self.tools[tool_call['name']]
            return tool.invoke(input=tool_call)
        else:
            # ParsedTollCallMessage
            return super()._internal_tool_call(tool_call=tool_call)

    def _get_tool_from_schemas(
        self,
        tool_schemas: Sequence[Union[ToolSchema, dict]]
    ) -> dict[str, BaseDefinedTool]:
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

        if executable_tools:
            logger.info(f"The '{self.name}' can execute {len(executable_tools)} tools.")
        return executable_tools
