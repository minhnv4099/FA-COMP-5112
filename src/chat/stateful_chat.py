#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
"""The chat with capability to remember the whole conversation of an unique config (thread_id)
It only works with text, NO tool call and structured output
"""

from __future__ import annotations

import logging
from typing import (
    Union,
    Sequence,
    Optional,
    TYPE_CHECKING,
    Generic,
)
from typing_extensions import override

from langchain_core.prompt_values import PromptValue
from langchain_core.runnables import RunnableConfig

from langchain_core.messages import BaseMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph
from langgraph.graph import END, START
from langgraph.types import RetryPolicy
from langgraph.runtime import Runtime

from src.registry import RegisterChat
from src.types import ContextT, StateT, OutputT, ToolSchema
from src.chat.mixin import GraphBasedMixin, StatefulChatMixin
from src.chat.base import BaseChat
from src.chat.tool_call_chat import ToolCallGenerateChat, ToolCallExecuteChat
from src.state.base import BaseState
from src.context.base import BaseContext
from src.utils.decorator import add_note_docstring

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph
    from langgraph.checkpoint.memory import BaseCheckpointSaver

logger = logging.getLogger(__name__)


@RegisterChat(module_path=__name__, name='stateful_chat')
class StatefulChat(
    StatefulChatMixin,
    GraphBasedMixin,
    BaseChat,
    Generic[StateT, ContextT, OutputT],
    bypass_override=True, show_5112=False
):
    """The Stateful chat class can retain the conversation"""

    config: Union[RunnableConfig, None]
    """Config containing ``thread_id``"""

    graph: CompiledStateGraph
    """The internal graph"""

    checkpointer: Union[BaseCheckpointSaver | None | bool]
    """Checkpointer memory to save state during the program.
    If None, clear state after each invocation.
    """

    state_schema: type[StateT]
    """State schema"""

    context_schema: type[ContextT]
    """Context schema"""

    output_schema: Union[dict, OutputT]
    """The output state for the internal graph"""

    def __init_subclass__(cls, **kwargs):
        ...

    def __init__(
        self,
        output_schema: Union[OutputT, dict] = None,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        # set default schema as general persistent chat
        self.state_schema = BaseState
        self.context_schema = BaseContext

        # output schema
        self.output_schema = output_schema if output_schema else self.state_schema

        self._initialize_config()
        self._initialize_checkpointer()
        self._build_internal_graph()

        self._set_system_behavior(
            config=self.config,
            system_prompt=self.system_template
        )

    @override
    def _build_internal_graph(self):
        # TODO: consider using self-defined graph "src/base/graph.py"
        self.graph_builder = StateGraph[StateT, ContextT, ..., ...](
            state_schema=self.state_schema,
            context_schema=self.context_schema,
            input_schema=self.state_schema,
            output_schema=self.output_schema
        )

        self.graph_builder.add_node(
            node='model_call',
            action=self.model_call,
            retry_policy=RetryPolicy(),
            metadata={
                'description': 'Actually call chat model'
            },
        )

        self.graph_builder.add_edge(START, 'model_call')
        self.graph_builder.add_edge('model_call', END)

        self.graph = self.graph_builder.compile(
            checkpointer=self.checkpointer,
            name=self.name
        )

    @add_note_docstring('A single node of internal graph')
    def model_call(
        self,
        state: StateT,
        config: Optional[RunnableConfig] = None,
        *,
        runtime: Optional[Runtime[ContextT]] = None,
        **kwargs
    ) -> dict:
        """An entrypoint node in the graph, invoking chat model

        Args:
            state:
                Current state of graph execution
            config:
                Used config to differ user/thread, making a conversation for each one
            runtime:
                Runtime variable giving access to context

        Returns:
            Updates state will be merged into the state schema
        """
        response = self.internal_invoke(
            input=state['messages'],
            config=config
        )

        return {'messages': response}

    @override
    def invoke(
        self,
        input: Union[str, BaseMessage, Sequence[BaseMessage], PromptValue],
        config: Optional[Union[RunnableConfig, dict]] = None,
        *,
        context: Optional[Runtime[ContextT]] = None,
        **kwargs,
    ) -> BaseMessage:
        """Exposing invoke function to outside

        Args:
            input:
                A message or list of messages. It is merged with the latest state before actually being passed to chat model.
            config:
                Config to set thread
            context:
                Context information

        Returns:
            The last message of the conversation. It can be ToolMessage, AIMessage, ParserMessage

        """
        if len(input) == 0:
            return AIMessage(content='Error: Input must have at least 1 token')

        config = config if config else self.config
        # using stream technique
        output = self.graph.invoke(
            input={'messages': input},  # type: ignore
            config=config,
            context=context,
        )

        return output['messages'][-1]

    @add_note_docstring("Can consider put in Mixin")
    def _set_system_behavior(
        self,
        config: Optional[Union[RunnableConfig, dict]],
        system_prompt: Optional[Union[SystemMessage, str]] = None
    ):
        """Set behavior for each chat with different config"""
        if not system_prompt:
            system_prompt = SystemMessage(content="You are a very helpful assistance.")
        elif isinstance(system_prompt, str):
            system_prompt = SystemMessage(content=system_prompt)

        self.put_state(
            config=config,
            values={
                'messages': [system_prompt, ]
            }
        )

    @add_note_docstring("Can consider put in Mixin")
    def put_state(
        self,
        config: Union[RunnableConfig, dict],
        values: dict
    ):
        self.graph.update_state(
            config=config,
            values=values
        )


@RegisterChat(module_path=__name__, name='tool_call_generate_stateful_chat')
class ToolCallGenerateStatefulChat(
    StatefulChat,
    StatefulChatMixin,
    GraphBasedMixin,
    ToolCallGenerateChat,
    Generic[StateT, ContextT, OutputT, ToolSchema]
):
    """The Stateful chat can generate tool call"""

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
            metadata={
                'description': 'Actually call chat model'
            },
        )

        self.graph_builder.add_node(
            node='tool_call',
            action=self.tool_call,
            metadata={
                'description': ''
            },
        )

        self.graph_builder.add_edge(START, 'model_call')
        self.graph_builder.add_edge('model_call', 'tool_call')
        self.graph_builder.add_edge('tool_call', END)

        self.graph = self.graph_builder.compile(
            checkpointer=self.checkpointer,
            name=self.name
        )

    def tool_call(
        self,
        state: Union[StateT],
        config: Optional[RunnableConfig] = None,
        *,
        runtime: Optional[Runtime[ContextT]] = None,
        **kwargs
    ) -> dict:
        """A node handling tool calls in last messages. To execute tool or parse args as structured output"""
        last_ai_message = state['messages'][-1]
        parser_messages = [
            self._internal_tool_call(tool_call=tool_call)
            for tool_call in last_ai_message.tool_calls
        ]

        return {'messages': parser_messages}


@RegisterChat(module_path=__name__, name='tool_call_execute_stateful_chat')
class ToolCallExecuteStatefulChat(
    ToolCallGenerateStatefulChat,
    StatefulChat,
    StatefulChatMixin,
    GraphBasedMixin,
    ToolCallExecuteChat,
    Generic[StateT, ContextT, OutputT, ToolSchema]
):
    """The Stateful chat can execute tool"""
