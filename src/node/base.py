#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import logging
from typing import Union, Generic, Optional, Any
from typing_extensions import override, overload

from langgraph.runtime import Runtime
from langchain_core.messages import BaseMessage, AIMessage

from src.registry import RegisterNode
from src.types import StateT, InputT, ContextT, OutputT, ToolSchema
from src.agent.base import BaseAgent

logger = logging.getLogger(__name__)


@RegisterNode(module_path=__name__, name='base_node')
class BaseNode(
    BaseAgent[StateT, ContextT, OutputT, ToolSchema],
    Generic[StateT, ContextT, InputT, OutputT, ToolSchema],
):
    # TODO: add docstring
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

    def get_desired_result(
        self,
        message: BaseMessage,
        keys_to_get: str,
        default: Any = None
    ) -> Any:
        """Get value from the message with the key

        Now only support single key.
        """
        if isinstance(message, AIMessage):
            return message.content

        return message.get_field(
            field=keys_to_get,
            default=default
        )

    def process_response(self, response: Any):
        if isinstance(response, str):
            return [response, ]

        return response
