#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
"""The React agent inherits the base agent with additional re-look to check
if it can provide the final response
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional, Union, TYPE_CHECKING, Generic, Literal, Sequence, Any

from langchain_core.prompts import SystemMessagePromptTemplate
from typing_extensions import override

from langchain_core.runnables import RunnableConfig
from langchain_core.messages import BaseMessage, SystemMessage, AIMessage, HumanMessage
from langgraph.graph import StateGraph
from langgraph.graph import END, START
from langgraph.runtime import Runtime
from langgraph.types import Command

from src.registry import RegisterAgent
from src.typing import StateT, ContextT, OutputT, ToolSchema, MappingLike
from src.chat.stateful_chat import ToolCallExecuteStatefulChat, LanguageModelInput
from src.utils.decorator import add_note_docstring

if TYPE_CHECKING:
    ...

logger = logging.getLogger(__name__)


@RegisterAgent(module=__name__, name='react_agent')
class LoopReactAgent(
    # ReactAgentMixin,
    ToolCallExecuteStatefulChat,
    Generic[StateT, ContextT, OutputT, ToolSchema]
):
    """The ReAct Agent can action and observe until meet conditions. It's non-stateful"""

    persistent_on_invoke: bool = True
    """If True, create a new thread each time invoking. Default to True (basic ReAct agent flow)"""

    max_attempts = 5
    """Max attempts loop"""

    num_tries = 0
    """Number tries loop"""

    def __init__(
        self,
        *args,
        persistent_on_invoke: Optional[bool] = None,
        option: Literal['1llm', '2llm'] = '1llm',
        max_attempts: int = 10,
        **kwargs
    ):
        self.max_attempts = max_attempts
        if option == '1llm':
            self._build_internal_graph = self._build_internal_graph_option_1
        else:
            self._build_internal_graph = self._build_internal_graph_option_2

        super().__init__(*args, **kwargs)
        if self.use_model and option == '2llm':
            self._separate_models()
            self.chat_model = self.chat_model_with_tools  # type: ignore

        self.persistent_on_invoke = persistent_on_invoke or self.persistent_on_invoke

    def _reset_thread(self):
        self.config['configurable']['thread_id'] = uuid.uuid1()

    def _build_internal_graph_option_1(self):
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
            metadata=None
        )

        self.graph_builder.add_node(
            node='observe_and_decide',
            action=self.observe_and_decide,
            metadata=None
        )
        self.graph_builder.add_node(
            node='tool_call',
            action=self.tool_call,
            metadata=None
        )

        self.graph_builder.add_edge(START, 'model_call')
        self.graph_builder.add_edge('model_call', 'observe_and_decide')
        self.graph_builder.add_edge('tool_call', 'model_call')

        self.graph = self.graph_builder.compile(
            checkpointer=self.checkpointer,
            name=self.name
        )

    def _build_internal_graph_option_2(self):
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
            metadata=None
        )

        self.graph_builder.add_node(
            node='observe_and_decide',
            action=self.observe_and_decide,
            metadata=None
        )
        self.graph_builder.add_node(
            node='tool_call',
            action=self.tool_call,
            metadata=None
        )

        self.graph_builder.add_node(
            node='response',
            action=self._response,
            metadata=None
        )

        self.graph_builder.add_edge(START, 'model_call')
        self.graph_builder.add_edge('model_call', 'observe_and_decide')
        self.graph_builder.add_edge('model_call', 'response')
        self.graph_builder.add_edge('tool_call', 'model_call')
        self.graph_builder.add_edge('response', END)

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
    ) -> BaseMessage:
        """The invocation function exposed to user

        Args:
            input: Input fed to the chat model.
                Types:

                - ``str``: Not support
                - ``dict``: Format chat template
                - ``PromptValue``: To messages -> {"messages": ...}.
                - ``BaseMessage, Sequence[BaseMessage]``: Pass directly -> {"messages": ...}.
            config: Config to separate streams of conversation. It's only useful when using with persistent chat.
            context: The sequence of string the model needs to stop generating if encounter

        Returns:
            The generated response.
        """
        if self.persistent_on_invoke:
            self._reset_thread()

        system_message = self._get_system_prompt()
        if system_message:
            input = [
                system_message,
                HumanMessage(content=input)
            ]

        if isinstance(input, dict):
            input = self.chat_template.invoke(
                input=input,
                config=config
            )

        return super().invoke(
            input=input,
            config=config,
            context=context
        )

    @add_note_docstring("Used for option 1 LLM")
    def observe_and_decide(
        self,
        state: Union[StateT],
        runtime: Optional[Runtime[ContextT]] = None,
        *,
        config: Optional[RunnableConfig] = None,
        **kwargs
    ) -> Command[Literal['tool_call', '__end__']]:
        """Using ``state``, ``runtime``, ``config`` to decide whether continue with tool call or end. \n
        It inspects the last AI message after executing tool and passing Tool Message back to conversation.\n
        This illustrates react agent loop with the capability to iteratively consider if the final answer is ready to flush.
        """
        last_message = state['messages'][-1]
        if not isinstance(last_message, AIMessage):
            raise ValueError(
                f"Expected AIMessage in output edges, but got {type(last_message).__name__!r}"
            )

        if len(last_message.tool_calls) == 1:
            tool_call = last_message.tool_calls[0]
            if self._is_structured_output(tool_call):
                self.num_tries = 0
                return Command(
                    update={
                        "messages": [self._internal_call_tool(tool_call), ],
                    },
                    goto=END,
                )

        # If there is no tool call or reach attempt limits, finish
        if self.num_tries <= self.max_attempts and last_message.tool_calls:
            self.num_tries += 1
            return Command(goto='tool_call')
        else:
            self.num_tries = 0
            return Command(goto=END)

    @add_note_docstring("Used for option 2 LLMs")
    def _separate_models(self):
        tool_schemas = self.fetch_schemas(self.tool_schemas)
        self.chat_model_with_tools = self.chat_model.bind_tools(
            tools=tool_schemas,
            strict=False,
        )

        if isinstance(structured_output_schema := self.chat_output, MappingLike):
            structured_output = self.fetch_schema(structured_output_schema)
        else:
            structured_output = self.chat_output

        self.chat_model_with_output = self.chat_model.bind_tools(
            tools=[structured_output,],
            strict=True,
            tool_choice='required'
        )

    @add_note_docstring("Used for option 2 LLMs")
    def _response(
        self,
        state: StateT,
        config: Optional[RunnableConfig] = None,
        *,
        runtime: Optional[Runtime[ContextT]] = None,
        **kwargs
    ) -> dict:
        response = self.chat_model_with_output.invoke(
            [HumanMessage(content=state['messages'][-1].content)]
        )

        return {'messages': [response,]}

    @override
    def _set_system_behavior(
        self,
        config: Optional[Union[RunnableConfig, dict]],
        system_prompt: Optional[Union[SystemMessage, SystemMessagePromptTemplate, str]] = None,
        sys_kwargs: Optional[dict[str, str]] = None
    ):
        ...


@RegisterAgent(module=__name__, name='react_stateful_agent')
class ReactStatefulAgent(
    LoopReactAgent,
    Generic[StateT, ContextT, OutputT, ToolSchema]
):
    """"""

    persistent_on_invoke: bool = False
