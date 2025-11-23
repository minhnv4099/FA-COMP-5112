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
from collections import defaultdict
from typing import Optional, Union, TYPE_CHECKING, Generic, Literal, Sequence, Any

from langchain_core.prompt_values import PromptValue
from langchain_core.prompts import SystemMessagePromptTemplate
from typing_extensions import override

from langchain_core.runnables import RunnableConfig
from langchain_core.messages import BaseMessage, SystemMessage, AIMessage, HumanMessage
from langgraph.graph import StateGraph
from langgraph.graph.state import END, START
from langgraph.runtime import Runtime
from langgraph.types import Command

from src.registry import RegisterAgent
from src.types import StateT, ContextT, OutputT, ToolSchema
from src.chat.stateful_chat import ToolCallExecuteStatefulChat, LanguageModelInput
from src.utils.decorator import add_note_docstring

if TYPE_CHECKING:
    ...

logger = logging.getLogger(__name__)


@RegisterAgent(module_path=__name__, name='react_agent')
class LoopReactAgent(
    # ReactAgentMixin,
    ToolCallExecuteStatefulChat,
    Generic[StateT, ContextT, OutputT, ToolSchema]
):
    """The ReAct Agent can action and observe until meet conditions. It's non-stateful"""

    persistent_on_invoke: bool
    """If True, create a new thread each time invoking. Default to True (basic ReAct agent flow)"""

    max_attempts = 5
    """Max attempts loop"""

    num_tries = 0
    """Number tries loop"""

    def __init__(
        self,
        *args,
        persistent_on_invoke: Optional[bool] = True,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.persistent_on_invoke = persistent_on_invoke

    def _reset_thread(self):
        self.config['configurable']['thread_id'] = uuid.uuid1()

    def _build_internal_graph(self):
        # TODO: consider using self-defined graph "src/base/graph.py"
        self.graph_builder = StateGraph[StateT, ContextT, ..., OutputT](
            state_schema=self.state_schema,
            context_schema=self.state_schema,
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
        # self.graph_builder.add_edge('model_call', '_response')
        # self.graph_builder.add_edge('_response', END)
        self.graph_builder.add_edge('tool_call', 'model_call')

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

        # TODO: can move to mixin
        if isinstance(input, str):
            if len(input) == 0:
                return AIMessage(content='Error: Input must have at least 1 token')
            raise ValueError("input can not be str")
        elif isinstance(input, dict):
            input = self.chat_template.invoke(
                input=input,
                config=config
            )
        elif isinstance(input, PromptValue):
            input = {'messages': input.to_messages()}
        elif isinstance(input, (BaseMessage, Sequence, list)):
            input = {'messages': input}

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
                f"Expected AIMessage in output edges, but got {type(last_message).__name__}"
            )

        if len(last_message.tool_calls) == 1:
            tool_call = last_message.tool_calls[0]
            if tool_call['name'] not in self.tools:
                self.num_tries = 0
                return Command(
                    update={
                        "messages": [self._internal_tool_call(tool_call), ],
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
        self.chat_model = self.chat_model.bind_tools(
            tools=self.tool_schemas,
            strict=False,
            tool_choice='any'
        )
        self.chat_model_with_outputs = self.chat_model.bind_tools(
            tools=self.chat_output,
            strict=True,
            tool_choice='any'
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
        response = self.chat_model_with_outputs.invoke(
            [HumanMessage(content=state['messages'][-2].content)]
        )

        return {'final_response': [response,]}

    @override
    def _set_system_behavior(
        self,
        config: Optional[Union[RunnableConfig, dict]],
        system_prompt: Optional[Union[SystemMessage, SystemMessagePromptTemplate, str]] = None,
        sys_kwargs: Optional[dict[str, str]] = None
    ):
        ...


@RegisterAgent(module_path=__name__, name='react_stateful_agent')
class ReactStatefulAgent(
    LoopReactAgent,
    Generic[StateT, ContextT, OutputT, ToolSchema]
):
    """"""

    persistent_on_invoke: bool = False
