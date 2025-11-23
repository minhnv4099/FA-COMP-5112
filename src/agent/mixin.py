#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from typing import Optional, Union, TYPE_CHECKING, Generic, Literal

from abc import ABC, ABCMeta
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph
from langgraph.graph.state import END, START
from langgraph.types import Command
from langgraph.runtime import Runtime

from src.types import StateT, ContextT, OutputT, ToolSchema
from src.utils.decorator import add_note_docstring


class ReactAgentMixin(
    ABC,
    Generic[StateT, ContextT, OutputT, ToolSchema],
    metaclass=ABCMeta
):
    """"""

    max_attempts = 5

    num_tries = 0

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
        self.graph_builder.add_edge('tool_call', 'model_call')

        self.graph = self.graph_builder.compile(
            checkpointer=self.checkpointer,
            name=self.name
        )

    @add_note_docstring("This function used to decide continue or finish a call")
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

        # TODO: solve tool calls
        if len(last_message.tool_calls) == 1:
            tool_call = last_message.tool_calls[0]
            if tool_call['name'] not in self.tools:
                self.num_tries = 0
                return Command(
                    update={
                        "messages": [self._internal_tool_call(tool_call),],
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
