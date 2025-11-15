#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
"""The ReAct agent inherits the base agent with additional re-look to check
if it can provide the final response
"""

from __future__ import annotations

import logging
from typing import Optional, Union, TYPE_CHECKING, Generic, Literal
from typing_extensions import override

from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph
from langgraph.graph.state import END, START
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.runtime import Runtime

from src.registry import RegisterAgent
from src.types import StateT, ContextT, OutputT, ToolSchema
from src.agent.base import BaseAgent
from src.utils.decorator import add_note_docstring

if TYPE_CHECKING:
    ...

logger = logging.getLogger(__name__)


@RegisterAgent(module_path=__name__, name='react_agent')
class LoopReactAgent(BaseAgent, Generic[StateT, ContextT, OutputT, ToolSchema]):
    # TODO: add docs
    """"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.max_attempts = 5
        self.num_tries = 0

    @override
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
            node='tool_call',
            action=self.tool_call,
            metadata=None
        )

        self.graph_builder.add_edge(START, 'model_call')
        self.graph_builder.add_conditional_edges(
            source='model_call',
            path=self.observe_and_decide,
            path_map={
                'tool_call': 'tool_call',
                'end': END
            }
        )
        self.graph_builder.add_edge('tool_call', 'model_call')

        self.graph = self.graph_builder.compile(
            checkpointer=InMemorySaver(),
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
    ) -> Literal['tool_call', 'end']:
        # TODO: add docs
        """"""
        last_message = state['messages'][-1]

        if not isinstance(last_message, AIMessage):
            raise ValueError(
                f"Expected AIMessage in output edges, but got {type(last_message).__name__}"
            )
        # If there is no tool call or limit attempts, then we finish
        if not last_message.tool_calls and self.num_tries < self.max_attempts:
            self.num_tries = 0
            return "end"

        self.num_tries += 1
        return 'tool_call'
