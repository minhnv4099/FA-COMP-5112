#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Optional, Union, TYPE_CHECKING
from typing_extensions import Generic

from langchain_core.runnables.graph import MermaidDrawMethod
from langgraph.checkpoint.memory import MemorySaver
from langgraph.config import RunnableConfig
from langgraph.graph import START, END
from langgraph.graph.state import StateGraph, CompiledStateGraph
from langgraph.runtime import Runtime
from langgraph.types import Command, Interrupt

from src.registry import fetch_registered, RegisterGraph
from src.types import StateT, ContextT, InputT, OutputT, NodeT
from src.utils.constants import ASSETS_DIR
from src.utils.exception import BreakGraphOperation, NoNodeError
from src.utils.decorator import add_note_docstring

if TYPE_CHECKING:
    from langchain_core.messages import BaseMessage
    from langgraph.types import StateSnapshot

logger = logging.getLogger(__name__)


@RegisterGraph(module_path=__name__, name='base')
class BaseGraph(
    Generic[StateT, ContextT, InputT, OutputT, NodeT]
):
    """The Base Graph class

    Every state channel could be declared in a particular node. Then the graph replies on schema to
    wrap corresponding state channels (e.g. 'state_schema', 'input_schema' of that node, type of state of the next node)
    """

    name: Optional[str]
    """Name of the graph"""

    graph_builder: StateGraph[StateT, ContextT, InputT, OutputT]
    """Graph map with node as an agent"""

    graph: CompiledStateGraph[StateT, ContextT, InputT, OutputT]
    """The compiled graph"""

    state_schema: type[StateT]
    """The overall state schema of the graph"""

    context_schema: type[ContextT]
    """The context state schema"""

    input_schema: type[InputT]
    """The input state schema"""

    output_schema: type[OutputT]
    """The output state schema"""

    nodes: list[NodeT]
    """List of nodes in graph"""

    def __init__(
        self,
        name: str,
        state_schema: Union[StateT, dict],
        context_schema: Union[ContextT, dict] = None,
        *,
        input_schema: Union[InputT, dict] = None,
        output_schema: Union[OutputT, dict] = None,
        nodes: Optional[list[NodeT]] = None,
        **kwargs,
    ):
        self.name = name
        self.state_schema = fetch_registered(state_schema)
        self.context_schema = fetch_registered(context_schema)
        self.input_schema = fetch_registered(input_schema)
        self.output_schema = fetch_registered(output_schema)

        self.nodes = nodes
        if not self.nodes:
            raise NoNodeError("No node found")

        self.graph_builder = StateGraph[StateT, ContextT, InputT, OutputT](
            state_schema=self.state_schema,
            context_schema=self.context_schema,
            input_schema=self.input_schema,
            output_schema=self.output_schema
        )

        self.is_interrupted = False
        self.state = None

        self.config = RunnableConfig(
            configurable={"thread_id": "form-1"},
            recursion_limit=200,
        )

    @property
    def compiled(self):
        return self.graph_builder.compiled

    def save_image_graph(self, file_path: Union[str, Path] = None):
        if not self.compiled:
            logger.critical(f"The graph isn't compiled yet. Compile it first!")
            return
        try:
            image_bytes = self.graph.get_graph().draw_mermaid_png(
                max_retries=5, retry_delay=2.,
                draw_method=MermaidDrawMethod.PYPPETEER
            )
            if not file_path:
                os.makedirs(ASSETS_DIR, exist_ok=True)
                file_path = os.path.join(ASSETS_DIR, f"{self.name}.png")

            with open(file_path, "wb") as f:
                f.write(image_bytes)

            logger.info(f"Write image of graph into '{file_path}'")

        except ValueError as e:
            print(e)

    def _add_nodes(self, nodes: list[NodeT]):
        for i, node in enumerate(nodes):
            name_node = standardize_name_node(node.name)
            self.graph_builder.add_node(
                node=name_node,
                action=node,
                metadata=node.metadata,
                input_schema=node.input_schema,
            )

    def _add_edges(self, nodes: list[str | NodeT]):
        for i, node in enumerate(nodes):
            name_node = standardize_name_node(node.name)

            for in_vertex in node.edges['in_coming']:
                if isinstance(in_vertex, str):
                    if "start" in in_vertex:
                        in_vertex = START
                else:
                    in_vertex = node.name
                self._add_edge(start_key=in_vertex, end_key=name_node)

            for out_vertex in node.edges['out_going']:
                if isinstance(out_vertex, str):
                    if "end" in out_vertex:
                        out_vertex = END
                else:
                    out_vertex = node.name
                self._add_edge(start_key=name_node, end_key=out_vertex)

    def _add_conditional_edges(self):
        raise NotImplementedError

    def _add_edge(self, start_key, end_key):
        try:
            self.graph_builder.add_edge(start_key, end_key)
        except ValueError as e:
            pass

    def init_graph(self):
        """Initialize the graph by adding nodes, connect them and compile"""

        self._add_nodes(self.nodes)
        self._add_edges(self.nodes)

        self.graph = self.graph_builder.compile(
            checkpointer=MemorySaver(),
            name=self.name,
            interrupt_before=[],
            interrupt_after=[],
            debug=False,
        )

        return self

    @add_note_docstring(docs="Used for only 'COMP-5112' project")
    def __call__(self, task, prompt, *args, **kwargs):
        try:
            if prompt:
                logger.info('Operate prompt')
                self.state = self.resume(input=prompt)
            else:
                logger.info('Operate task')
                self.state = self._invoke(input=task)

        except BreakGraphOperation as e:
            self.state = e.state

        if "__interrupt__" in self.state:
            self.state = self.state['__interrupt__'][0].value

        images = self.state.get('rendered_images', None)
        if not images:
            images = [None, None, None, None]

        result = [
            self.state['msg'],
            self.state.get('current_script', None),
            'Conversation'
            # AgentAsNode.get_conversation(self.state['messages']),
        ]
        result.extend(images)

        return result

    @add_note_docstring(docs="Used for only 'COMP-5112' project")
    def _invoke(
        self,
        input: Union[StateT, InputT, str],
        context: Runtime[ContextT] = None,
        config: Optional[RunnableConfig] = None,
    ):
        inputs = self._convert_input_with_task_key(input)

        try:
            self.state = self.invoke(input=inputs, context=context, config=config)

            while True:
                additional_prompt = input("Enter additional prompt (e.g. change color to red): ")
                self.state = self.resume(additional_prompt)

        except BreakGraphOperation as e:
            self.state = e.state
            # AgentAsNode.log_conversation(logger, e.state['messages'])
            return self.state.get('msg', None)

    def invoke(
        self,
        input: StateT,
        config: Optional[RunnableConfig] = None,
        *,
        context: Optional[Runtime[ContextT]] = None,
    ) -> Union[OutputT, Interrupt]:
        """Invoke the graph, get any result (state or interrupted value)

        Args:
            input (StateT, str):
                The input to pass to graph execution
            context:
                The context goes through the execution
            config:
                The config goes through the execution
        Returns:
            Union[OutputT, StateT, Interrupt]
        """

        inputs = self._convert_input_with_task_key(input)
        config = config if config else self.config
        response: OutputT = self.graph.invoke(
            input=inputs,
            context=context,
            config=config
        )

        self.state = self.get_state(config)

        return response

    @add_note_docstring(docs="Used for only 'COMP-5112' project")
    def _convert_input_with_task_key(self, inputs):
        if isinstance(inputs, str):
            inputs = {'task': inputs}

        return inputs

    def resume(
        self,
        input: Union[StateT, InputT, dict],
        config: Optional[RunnableConfig] = None,
    ):
        return self.invoke(
            Command(resume=input),
            config=config
        )

    def pretty_print_dict(self):
        for k, v in self.graph.__dict__.items():
            print(f"{k}\n\t{v}\n{'=' * 50}")

    def get_state(self, config: Optional[Union[RunnableConfig, dict]] = None) -> StateSnapshot:
        return self.graph.get_state(config if config else self.config)

    def get_messages(self, config: Optional[Union[RunnableConfig, dict]] = None) -> list[BaseMessage]:
        return self.get_state(config).values.get('messages', [])

    def print_conversation(self, config=None):
        for m in self.get_messages(config):
            m.pretty_print()


def standardize_name_node(name):
    return name.replace(' ', '_').lower()
