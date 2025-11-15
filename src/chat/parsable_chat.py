#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations

import logging

from typing import (
    Union,
    Any,
    TYPE_CHECKING,
    Generic,
    Iterable,
    Optional,
    Literal
)
from typing_extensions import override, deprecated

from langgraph.types import RetryPolicy
from langgraph.graph import StateGraph
from langgraph.graph.state import END, START
from langgraph.checkpoint.memory import InMemorySaver

from src.registry import RegisterChat, fetch_registered
from src.types import (
    StateT,
    OutputT,
    ContextT,
    SchemaLike,
    ToolSchema,
    OmegaList,
    OmegaDict
)
from src.chat import PersistentChat
from src.message.parsed_tool_call import ParsedTollCallMessage
from src.utils.decorator import add_note_docstring, must_override

if TYPE_CHECKING:
    from langgraph.runtime import Runtime
    from langchain_core.runnables import RunnableConfig
    from langchain_core.tools.base import ToolCall

logger = logging.getLogger(__name__)


@RegisterChat(module_path=__name__, name='tool_call_chat')
class ParseToolCallChat(
    PersistentChat[StateT, ContextT],
    Generic[StateT, ContextT, OutputT, ToolSchema],
    bypass_override=True
):
    # TODO: add docs
    """The Tool Call Chat class"""

    output_schema: list[Union[dict, OutputT]]
    """The structure output the chat model should return"""

    output_schema_as_tool: bool
    """Bind `output_schema` as tool, providing more flexibility. 
    In some cases, the output schema can be bound by ``.with_structure()``"""

    tool_schemas: list[Union[ToolSchema, dict]] = None,
    """Tool schema"""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

    def __init__(
        self,
        *args,
        output_schema: list[Union[OutputT, dict]] = None,
        output_schema_as_tool: bool = True,
        tool_schemas: list[Union[ToolSchema, dict]] = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        # output schema
        self.output_schema = output_schema
        self.output_schema_as_tool = output_schema_as_tool

        # tool schema
        self.tool_schemas = tool_schemas

        # bind schemas to the chat model
        if self.chat_model:
            schemas = self._validate_schemas()
            self.chat_model = self.chat_model.bind_tools(
                tools=schemas, strict=False
            )

    @override
    def _build_internal_graph(self):
        # TODO: consider using self-defined graph "src/base/graph.py"
        self.graph_builder = StateGraph[StateT, ContextT, ..., ...](
            state_schema=self.state_schema
        )

        self.graph_builder.add_node(
            node='model_call',
            action=self.model_call,
            retry_policy=RetryPolicy(),
            metadata=None
        )

        self.graph_builder.add_node(
            node='tool_call',
            action=self.tool_call,
            metadata=None
        )

        self.graph_builder.add_edge(START, 'model_call')
        self.graph_builder.add_edge('model_call', 'tool_call')
        self.graph_builder.add_edge('tool_call', END)

        self.graph = self.graph_builder.compile(
            checkpointer=InMemorySaver(),
            name=self.name
        )

    def tool_call(
        self,
        state: Union[StateT],
        config: Optional[RunnableConfig] = None,
        *,
        runtime: Optional[Runtime[ContextT]] = None,
        **kwargs
    ) -> dict[Literal['messages'], Any]:
        # TODO: add docs
        """"""
        last_ai_message = state['messages'][-1]
        parser_messages = [
            self._internal_tool_call(tool_call=tool_call)
            for tool_call in last_ai_message.tool_calls
        ]

        return {'messages': parser_messages}

    def _internal_tool_call(
        self,
        tool_call: ToolCall,
        **kwargs,
    ) -> ParsedTollCallMessage:
        """Return dict result with items as args in tool_call. It acts as structured output but use tool call mechanism"""

        return ParsedTollCallMessage(
            content=self.get_pretty_prep(tool_call['args']),
            raw_content=tool_call['args'],
            tool_call_id=tool_call['id'],
        )

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

        return schemas

    def _convert_to_list(self, seq: Union[Any, Iterable[Any]]) -> list[Any]:
        if seq and not isinstance(seq, OmegaList):
            seq = [seq, ]

        return seq or []

    def fetch_schema(
        self,
        schema: Union[dict, SchemaLike]
    ) -> Union[None, SchemaLike]:

        if not isinstance(schema, OmegaDict):
            return schema

        return fetch_registered(metadata=schema)
