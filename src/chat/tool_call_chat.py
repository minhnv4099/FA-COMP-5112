#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations

import logging

from typing import Union, Any, TYPE_CHECKING
from typing_extensions import override

from langchain_core.messages import ToolMessage

from src.registry import RegisterChat, fetch_registered
from src.types import OutputT, SchemaLike, OmegaDict, ToolSchema
from src.chat import PersistentChat
from src.utils.decorator import add_note_docstring, must_override

if TYPE_CHECKING:
    from langchain_core.messages import AIMessage
    from langchain_core.tools.base import ToolCall
    from langgraph.runtime import Runtime
    from langchain_core.runnables import RunnableConfig
    from src.base.state import BaseState
    from src.base.chat import BaseChatAssistance

logger = logging.getLogger(__name__)


@RegisterChat(module_path=__name__, name='tool_call_chat')
class ToolCallChat(PersistentChat, bypass_override=True):
    """The Tool Call Chat class"""
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

    def __init__(
        self,
        *args,
        tool_schemas: ToolSchema | list[Union[ToolSchema, dict]] = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.tool_schemas = tool_schemas

        schemas = self._validate_schemas()
        self._bind_schemas(schemas=schemas)

    @must_override
    def _validate_schemas(self) -> list[OutputT]:
        """Validate output schemas to chat model"""

        self.tool_schemas = self._convert_to_list(seq=self.tool_schemas)
        self.output_schema = self._convert_to_list(seq=self.output_schema)

        schemas = self.tool_schemas + self.output_schema
        schemas = [
            self.fetch_schema(tool_schema)
            for tool_schema in schemas
        ]

        schemas = list(filter(lambda x: x, schemas))

        if schemas:
            logger.warning(f"The schemas '{schemas}' are just (or treated as) tool schemas, which requires "
                           f"'ToolMessage' after 'AIMessage' that have tool calls with associative tool_call_id.")

        self.output_schema = schemas

        return self.output_schema

    def fetch_schema(self, schema: Union[dict, SchemaLike]) -> Union[None, SchemaLike]:
        if not isinstance(schema, OmegaDict):
            return schema

        return fetch_registered(metadata=schema)

    def _bind_schemas(self, schemas):
        """Bind schemas to chat model, and force model to always use the first schema"""

        self.chat_model = self.chat_model.bind_tools(
            tools=schemas,
            # tool_choice=schemas[0]
        )

    @override
    def model_call(
        self,
        state: BaseState,
        runtime: Runtime,
        config: RunnableConfig,
        *args,
        **kwargs
    ):
        """"""
        logger.info(f"Number of messages: {len(state['messages'])}")
        inputs = state['messages']

        response = self.chat_model.invoke(input=inputs, config=config)
        tool_messages = self.tool_call(response.tool_calls)

        return {'messages': [response, *tool_messages]}

    def tool_call(self, tool_calls: list[ToolCall]) -> list[ToolMessage]:
        tool_messages = []

        for tool_call in tool_calls:
            tool_message = ToolMessage(
                content=self.get_pretty_prep(tool_call['args']),
                tool_call_id=tool_call['id']
            )
            tool_messages.append(tool_message)

        return tool_messages
