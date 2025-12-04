#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
"""The chat with capability to remember the whole conversation of a unique config (thread_id)
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
    cast,
    Any
)
from typing_extensions import override

from langchain_core.prompt_values import PromptValue
from langchain_core.runnables import RunnableConfig

from langchain_core.messages import BaseMessage, SystemMessage, AIMessage
from langchain_core.prompts import SystemMessagePromptTemplate
from langgraph.graph import StateGraph
from langgraph.graph import END, START
from langgraph.types import RetryPolicy
from langgraph.runtime import Runtime

from src.registry import RegisterChat
from src.typing import ContextT, StateT, OutputT, ToolSchema
from src.chat.mixin import GraphBasedMixin, StatefulChatMixin
from src.chat.base import BaseChat, LanguageModelInput
from src.chat.tool_call_chat import ToolCallGenerateChat, ToolCallExecuteChat
from src.state.base import BaseState
from src.context.base import BaseContext
from src.utils.decorator import add_note_docstring
from src.utils.exception import EmptyMessage

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph
    from langgraph.checkpoint.memory import BaseCheckpointSaver
    from src.message.parsed_tool_call import ParsedTollCallMessage

logger = logging.getLogger(__name__)


@RegisterChat(module=__name__, name='stateful_chat')
class StatefulChat(
    StatefulChatMixin,
    GraphBasedMixin,
    BaseChat,
    Generic[StateT, ContextT, OutputT],
    bypass_override=True, show_5112=False
):
    """The Stateful chat can retain the conversation"""

    config: Optional[RunnableConfig]
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

        if self.system_template:
            self._set_system_behavior(
                config=self.config,
                system_prompt=cast(
                    "SystemMessage",
                    self.system_template.format(**kwargs.get('system_template_dict', dict()))
                )
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
    ) -> dict[str, Any]:
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

        return {'messages': [response,]}

    @override
    def validate_input(self, input: LanguageModelInput) -> dict:
        if isinstance(input, dict):
            input = input
        elif isinstance(input, str):
            if len(input) == 0:
                raise EmptyMessage('Error: Input must have at least 1 token')
            input = {'messages': input}
        elif isinstance(input, PromptValue):
            input = {'messages': input.to_messages()}
        elif (isinstance(input, BaseMessage) or
              (isinstance(input, list) and all(isinstance(m, BaseMessage) for m in input))):
            input = {'messages': input}
        else:
            msg = f"Expect type {repr(LanguageModelInput)!r}, but got {type(input)!r}"
            raise ValueError(msg) from None

        return input

    @override
    def invoke(
        self,
        input: LanguageModelInput,
        config: Optional[Union[RunnableConfig, dict]] = None,
        *,
        context: Optional[Runtime[ContextT]] = None,
        **kwargs,
    ) -> AIMessage:
        """The invocation function exposed to user

        Args:
            input: Input fed to the chat model.
                Types:

                - ``dict``: Like state, pass directly, all keys must be valid.
                - ``str``: Content of the human message -> {"messages": ...}.
                - ``PromptValue``: To messages -> {"messages": ...}.
                - ``BaseMessage, Sequence[BaseMessage]``: Pass directly -> {"messages": ...}.
                It is merged with the latest state before actually being passed to chat model.
            config: Config to separate streams of conversation. It's only useful when using with persistent chat.
            context: The sequence of string the model needs to stop generating if encounter

        Returns:
            The generated response.
        """
        config = config if config else self.config
        try:
            input = self.validate_input(input)
        except EmptyMessage as e:
            return AIMessage(content=str(e))

        output = self.graph.invoke(
            input=input,  # type: ignore
            config=config,
            context=context,
        )

        return output['messages'][-1]

    @add_note_docstring("Can consider put in Mixin")
    def _set_system_behavior(
        self,
        config: Optional[Union[RunnableConfig, dict]],
        system_prompt: Optional[Union[SystemMessage, SystemMessagePromptTemplate, str]] = None,
        sys_kwargs: Optional[dict[str, str]] = None
    ):
        """Set behavior for each chat with different config"""
        if not system_prompt:
            system_prompt = SystemMessage(content="You are a very helpful assistance.")
        elif isinstance(system_prompt, str):
            system_prompt = SystemMessage(content=system_prompt)
        elif isinstance(system_prompt, SystemMessagePromptTemplate):
            system_prompt = system_prompt.format(
                **sys_kwargs if sys_kwargs else dict()
            )

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


@RegisterChat(module=__name__, name='tool_call_generate_stateful_chat')
class ToolCallGenerateStatefulChat(
    StatefulChat,
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
                'description': 'Model call node'
            },
        )

        self.graph_builder.add_node(
            node='tool_call',
            action=self.tool_call,
            metadata={
                'description': 'Tool call node'
            },
        )

        self.graph_builder.add_edge(START, 'model_call')
        self.graph_builder.add_edge('model_call', 'tool_call')
        self.graph_builder.add_edge('tool_call', END)

        self.graph = self.graph_builder.compile(
            checkpointer=self.checkpointer,
            name=self.name
        )

    @override
    def invoke(
        self,
        input: LanguageModelInput,
        config: Optional[Union[RunnableConfig, dict]] = None,
        *,
        context: Optional[Runtime[ContextT]] = None,
        **kwargs,
    ) -> AIMessage | ParsedTollCallMessage:
        """The invocation function exposed to user

        Args:
            input: Input fed to the chat model.
                Types:

                - ``dict``: Like state, pass directly, all keys must be valid.
                - ``str``: Content of the human message -> {"messages": ...}.
                - ``PromptValue``: To messages -> {"messages": ...}.
                - ``BaseMessage, Sequence[BaseMessage]``: Pass directly -> {"messages": ...}.
                It is merged with the latest state before actually being passed to chat model.
            config: Config to separate streams of conversation. It's only useful when using with persistent chat.
            context: The sequence of string the model needs to stop generating if encounter

        Returns:
            The generated response.
        """
        return super().invoke(
            input=input,
            config=config,
            context=context
        )

    @add_note_docstring("Tool call node of the internal graph")
    def tool_call(
        self,
        state: Union[StateT],
        config: Optional[RunnableConfig] = None,
        *,
        runtime: Optional[Runtime[ContextT]] = None,
        **kwargs
    ) -> Union[dict[str, list[ParsedTollCallMessage]], None]:
        """A node handling tool calls in last messages. To execute tool or parse args as structured output"""
        last_ai_message = state['messages'][-1]
        tool_based_messages = [
            self._internal_call_tool(tool_call=tool_call)
            for tool_call in last_ai_message.tool_calls
        ]

        return {'messages': tool_based_messages}


@RegisterChat(module=__name__, name='tool_call_execute_stateful_chat')
class ToolCallExecuteStatefulChat(
    ToolCallGenerateStatefulChat,
    # Inherit `_internal_tool_call`
    ToolCallExecuteChat,
    Generic[StateT, ContextT, OutputT, ToolSchema]
):
    """The Stateful chat can execute tool"""
