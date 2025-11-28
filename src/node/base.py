#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import logging
from typing import Union, Generic, Optional, Any, TYPE_CHECKING, TypeVar, Literal, Sequence
from typing_extensions import override, overload

from langgraph.runtime import Runtime
from langchain_core.messages import BaseMessage, AIMessage

from src.registry import RegisterNode
from src.types import StateT, InputT, ContextT, OutputT, ToolSchema
from src.agent.react_loop import LoopReactAgent

if TYPE_CHECKING:
    ...

logger = logging.getLogger(__name__)


@RegisterNode(module_path=__name__, name='base_node')
class BaseNode(
    LoopReactAgent,
    Generic[StateT, ContextT, InputT, OutputT, ToolSchema]
):
    """The Base Node class"""

    node_name: str
    """Node name"""

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

    def __init_subclass__(cls, node_name: str, **kwargs):
        cls.node_name = node_name

    def __init__(
        self,
        *args,
        input_schema: Union[InputT, StateT] = None,
        edges: dict = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.edges = edges
        self.input_schema = self.fetch_schema(
            schema=input_schema if input_schema else self.state_schema
        )

    @override
    def __call__(
        self,
        *args,
        state: Union[StateT, InputT],
        runtime: Optional[Runtime[ContextT]],
        **kwargs
    ):
        raise NotImplementedError

