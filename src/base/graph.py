#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import os
import logging
from pathlib import Path
from typing import Optional, Union
from typing_extensions import Generic

from langchain_core.runnables.graph import MermaidDrawMethod
from langgraph.config import RunnableConfig
from langgraph.graph import START, END
from langgraph.graph.state import StateGraph, CompiledStateGraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from .agent import AgentAsNode
from .mapping import register, fetch_schema
from ..utils import ASSETS_DIR
from ..utils import BreakGraphOperation, NoConnectionEdges
from ..utils import StateT, ContextT, InputT, OutputT, NodeT

logger = logging.getLogger(__name__)


@register(name='base', type='graph')
class BaseGraph(Generic[StateT, ContextT, InputT, OutputT, NodeT]):
    """The Base Graph class

    Every state channel could be declared in a particular node. Then the graph replies on schema to
    wrap corresponding state channels (e.g. 'state_schema', 'input_schema' of that node, type of state of the next node)
    """

    name: str
    """Name of graph"""

    graph: StateGraph[StateT, ContextT, InputT, OutputT]
    """Graph map with node as an agent"""

    complied_graph: CompiledStateGraph[StateT, ContextT, InputT, OutputT]
    """The compiled graph"""

    name: Optional[str]
    """Name of the graph"""

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
            state_schema: StateT | dict,
            context_schema: ContextT | None = None,
            *,
            input_schema: InputT | None = None,
            output_schema: OutputT | None = None,
            nodes: Optional[list[NodeT]] = None,
            **kwargs,
    ):
        self.name = name
        self.state_schema = fetch_schema(state_schema)
        self.context_schema = fetch_schema(context_schema)
        self.input_schema = fetch_schema(input_schema)
        self.output_schema = fetch_schema(output_schema)

        self.nodes = nodes
        if not self.nodes:
            logger.critical("No any nodes")

        self.graph = StateGraph[StateT, ContextT, InputT, OutputT](
            state_schema=self.state_schema,
            context_schema=self.context_schema,
            input_schema=input_schema,
            output_schema=output_schema
        )

        self.is_interrupted = False
        self.state = None
        self.config = {
            "configurable": {"thread_id": "form-1"},
            'recursion_limit': 200
        }

    @property
    def compiled(self):
        return self.graph.compiled

    def save_image_graph(self, file_path: Union[str, Path] = None):
        if not self.compiled:
            logger.critical(f"The graph isn't compiled yet. Compile it first!")
            return
        try:
            image_bytes = self.complied_graph.get_graph().draw_mermaid_png(
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

    def standardize_name_node(self, name):
        return name.replace(' ', '_').lower()

    def _add_nodes(self, nodes: list[NodeT]):
        for i, node in enumerate(nodes):
            name_node = self.standardize_name_node(node.name)
            self.graph.add_node(
                node=name_node,
                action=node,
                metadata=node.metadata,
                input_schema=node.input_schema
            )

    def _add_edges(self, nodes: list[NodeT]):
        for i, node in enumerate(nodes):
            name_node = self.standardize_name_node(node.name)
            for in_vertex in node.edges['in_coming']:
                if isinstance(in_vertex, str):
                    if "start" in in_vertex:
                        in_vertex = START
                    self._add_edge(start_key=in_vertex, end_key=name_node)

            for out_vertex in node.edges['out_going']:
                if isinstance(out_vertex, str):
                    if "end" in out_vertex:
                        out_vertex = END
                    self.graph.add_edge(start_key=name_node, end_key=out_vertex)

    def _add_conditional_edges(self):
        raise NotImplementedError

    def _add_edge(self, start_key, end_key):
        try:
            self.graph.add_edge(start_key, end_key)
        except NoConnectionEdges:
            pass

    def init_graph(self):
        """Initialize the graph by adding nodes, connect them and compile"""
        self._add_nodes(self.nodes)
        self._add_edges(self.nodes)

        self.complied_graph = self.graph.compile(checkpointer=MemorySaver())

    def __call__(self, task, prompt, *args, **kwargs):
        message = "Successful"
        try:
            if prompt:
                logger.info('Operate prompt')
                self.state = self._resume(prompt)
            else:
                logger.info('Operate task')
                self.state = self._invoke(task)
        except BreakGraphOperation as e:
            self.state = e.state
            message = e.msg

        images = self.state.get('rendered_images', None)
        if not images:
            images = [None, None, None, None]

        result = [
            message,
            self.state.get('current_script', None),
            AgentAsNode.get_conversation(self.state['messages']),
        ]
        result.extend(images)

        return result

    def invoke(
            self,
            inputs: Union[StateT, InputT, str],
            context: Optional[ContextT] = None,
            config: Optional[RunnableConfig] = None,
    ):
        if isinstance(inputs, str):
            inputs = {'task': inputs}

        try:
            self.state = self.complied_graph.invoke(
                input=inputs,
                config=self.config,
                context=context,
            )
            while True:
                additional_prompt = input("Enter additional prompt (e.g. change color to red): ")

                self.state = self._resume(additional_prompt)

        except BreakGraphOperation as e:
            self.state = e.state
            AgentAsNode.log_conversation(logger, e.state['messages'])
            return e.state, e.msg

    def _invoke(
            self,
            input: Union[StateT, InputT, str],
            context: Optional[ContextT] = None,
            config: Optional[RunnableConfig] = None,
    ):
        if isinstance(input, str):
            input = {'task': input}

        self.state = self.complied_graph.invoke(
            input=input,
            config=self.config,
            context=context,
        )

        # AgentAsNode.log_conversation(logger, state['messages'])
        return self.state

    def _resume(self, input):
        return self.complied_graph.invoke(Command(resume=input), config=self.config)

    def pretty_print_dict(self):
        for k, v in self.graph.__dict__.items():
            print(f"{k}\n\t{v}\n{'=' * 50}")
