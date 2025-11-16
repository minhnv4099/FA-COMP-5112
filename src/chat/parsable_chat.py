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
from json import dumps, loads
from json.decoder import JSONDecodeError
from typing import (
    Union,
    Any,
    TYPE_CHECKING,
    Generic,
    Iterable,
    Optional,
    Literal
)
from typing_extensions import override

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
from src.utils.decorator import must_override, add_note_docstring

if TYPE_CHECKING:
    from langgraph.runtime import Runtime
    from langchain_core.runnables import RunnableConfig
    from langchain_core.tools.base import ToolCall

logger = logging.getLogger(__name__)


@RegisterChat(module_path=__name__, name='tool_call_chat')
class ParseToolCallChat(
    PersistentChat[StateT, ContextT, OutputT],
    Generic[StateT, ContextT, OutputT, ToolSchema],
    bypass_override=True
):
    # TODO: add docs
    """The Tool Call Chat class"""

    tool_schemas: list[Union[ToolSchema, dict]]
    """Tool schemas including output schema"""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

    def __init__(
        self,
        *args,
        tool_schemas: list[Union[ToolSchema, dict]] = None,
        **kwargs
    ):
        # tool schemas
        self.tool_schemas = tool_schemas

        super().__init__(*args, **kwargs)

        # bind schemas to the chat model
        if self.chat_model:
            schemas = self._validate_schemas()
            self.chat_model = self.chat_model.bind_tools(
                tools=schemas, strict=False
            )

    @override
    def _build_internal_graph(self):
        # TODO: consider using self-defined graph "src/base/graph.py"
        self.graph_builder = StateGraph[StateT, ContextT, ..., OutputT](
            state_schema=self.state_schema,
            context_schema=self.context_schema,
            input_schema=self.state_schema,
            output_schema=self.output_schema
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
        """A node handling tool calls in last messages. To execute tool or parse args as structured output"""
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
        """The actual handler tool call. This chat class just parses args of tool call into structure output

        Args:
            tool_call:
                Contains information about the tool

        Returns:
            ParsedTollCallMessage subclass of ToolMessage whose content is args in ``tool_call``
        """
        return ParsedTollCallMessage(
            raw_content=tool_call['args'],
            content=self.get_pretty_prep(tool_call['args']),
            tool_call_id=tool_call['id'],
        )

    def get_pretty_prep(self, content: Any):
        """Try to get pretty content"""
        try:
            if isinstance(content, str):
                text = dumps(loads(
                    self._parse_json_content(content)), indent=4
                )
            else:
                text = dumps(content, indent=4)
            return text
        except (JSONDecodeError, TypeError) as e:
            return content

    def _parse_json_content(self, text: str):
        """Parse the structured output from text content"""
        import json, re

        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z]*", "", text).strip("` \n")
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except ValueError:
                pass

        return text
    @must_override
    def _validate_schemas(self) -> list[ToolSchema]:
        """Validate output schemas to chat model"""
        self.tool_schemas = self._convert_to_list(seq=self.tool_schemas)
        # get all schemas, do matter output schema and tool schema
        # let model know schemas
        schemas = [
            self.fetch_schema(schema)
            for schema in self.tool_schemas
        ]

        # filter none schema
        schemas = list(filter(lambda x: x, schemas))
        if schemas:
            ...
            # logger.warning(f"The schemas '{schemas}' are just (or treated as) tool schemas, which requires "
            #                f"'ToolMessage' after 'AIMessage' that have tool calls with associative tool_call_id.")

        return schemas

    def fetch_schema(
        self,
        schema: Union[dict, SchemaLike]
    ) -> Union[None, SchemaLike]:
        if not isinstance(schema, OmegaDict):
            return schema

        return fetch_registered(metadata=schema)

    def _convert_to_list(self, seq: Union[Any, Iterable[Any]]) -> list[Any]:
        if seq and not isinstance(seq, OmegaList):
            seq = [seq, ]

        return seq or []
