#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import logging
from typing import Union, Generic

from langgraph.runtime import Runtime
from typing_extensions import override

from src.base.agent import BaseAgent
from src.registry import RegisterAgent
from src.state import DEFAULT_STATE_SCHEMA
from src.types import StateT, InputT, ContextT, OutputT, ToolSchema
from src.utils.decorator import must_override

logger = logging.getLogger(__name__)

module_path = __name__


class BaseNode(BaseAgent, Generic[StateT, ContextT, InputT, OutputT]):
    """The Base Node class"""

    input_schema: Union[InputT, StateT]
    """Input state schema to the node"""

    edges: dict[str, tuple[str]]
    """In-coming and out-going edges connected with this node
    ```
    {
        "in_coming" : ('name_node_1', 'name_node_2'),
        "out_going" : ('name_node_3', 'name_node_4')
    }
    ```
    This is only used to display directions. MUST be empty when invoking graphs
    """


@RegisterAgent(module_path=module_path, name='agent_as_node')
class AgentAsNode(BaseNode, Generic[StateT, ContextT, InputT, OutputT, ToolSchema]):
    """The Agent As Node class

    An agent has an LLM acting as brain and tools, allowing to interact with external knowledge, environment.
    """

    def __init_subclass__(cls, node_name: str = None, use_model: bool = True):
        ...

    def __init__(
            self,
            *args,
            input_schema: Union[InputT, StateT] = DEFAULT_STATE_SCHEMA,
            edges: dict = None,
            **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.edges = edges
        self.input_schema = self.fetch_schema(input_schema)

    @override
    @must_override
    def __call__(
            self,
            state: InputT | StateT,
            runtime: Runtime[ContextT] = None,
            **kwargs
    ):
        raise NotImplementedError
