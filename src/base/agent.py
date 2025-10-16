#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from typing import Optional, Union, Generic, Any

from langchain.chat_models import init_chat_model
from langchain.chat_models.base import BaseChatModel
from langgraph.config import RunnableConfig
from langgraph.runtime import Runtime
from pydantic import BaseModel
from typing_extensions import Annotated, TypeVar

from .state import BaseState

StateT = TypeVar("StateT", bound=BaseState, default=BaseState)
ContextT = TypeVar("ContextT", bound=Union[BaseState, None], default=None)
InputT = TypeVar("InputT", bound=BaseState, default=BaseState)
OutputT = TypeVar("OutputT", bound=BaseState, default=BaseState)


class AgentWithoutLLM(BaseModel):
    name: str
    """Name of the unique name/node, used to identify node in a graph"""

    metadata: dict
    """Metadata of node used to provide additional information"""

    input_schema: Any
    """Input schema the node expect"""

    edges: dict[str, tuple[str]]
    """Dictionary contains in-coming and out-going edge to and from this node"""

    tool_schemas: list
    """List of tool schemas equipped to the agent"""


class AgentAsNodeConfig(AgentWithoutLLM):
    """
    The Agent as Node Config class
    """
    output_schema: Any
    """Enforced schema so that models returns"""

    model_name: str
    """Name of model to call API"""

    model_provide: str
    """Provider of the model"""

    model_api_key: str
    """API KEY"""

    output_schema_as_tool: bool
    """Use output_schema as a tool"""

    chat_model: Any
    """Pre-defined chat mode"""


class BaseAgent:
    """The Base Agent class"""
    name: Annotated[str, "Name of the agent"]
    """Unique name of the class"""


class AgentAsNode(BaseAgent, Generic[StateT, ContextT, InputT, OutputT]):
    """The Agent As Node class

    An agent has an LLM acting as brain and tools, allowing to interact with external knowledge, environment.
    """

    metadata: dict[str, str] = None
    """Metadata used when attach to a graphs"""

    input_schema: Union[InputT, StateT] = None
    """Input state schema to the node"""

    edges: dict[str, tuple] = None
    """In-coming and out-going edges connected with this node"""

    tool_schemas: list = []
    """Tools equip to LLM (chat model)"""

    output_schema: Any = None
    """The structure output the chat model should return"""

    model_name: str = None
    """Name of LLM (e.g. ``gpt-4o``, ``gpt-4o-mini``)"""

    model_provider: str = None
    """Provide of used model (e.g. ``openai``, ``google``)"""

    model_api_key: str = None
    """API key"""

    output_schema_as_tool: bool = None
    """Bind `output_schema` as tool, providing more flexibility"""

    chat_model: BaseChatModel = None
    """The chat model, useful when it's shared across multiple nodes/places"""

    def __init_subclass__(cls, name: str = None, **kwargs):
        cls.name = name

    def __init__(
            self,
            metadata: dict = None,
            input_schema: InputT = None,
            edges: dict[str, tuple[str]] = None,
            tool_schemas: list = None,
            output_schema: Any = None,
            model_name: str = None,
            model_provider: str = None,
            model_api_key: str = None,
            output_schema_as_tool: bool = None,
            chat_model: BaseChatModel = None,
            **kwargs,
    ):
        self.metadata = metadata

        self.chat_model = chat_model
        self.model_name = model_name
        self.model_provider = model_provider
        self.model_api_key = model_api_key

        self.edges = edges
        self.input_schema = input_schema
        self.tool_schemas = tool_schemas
        self.output_schema = output_schema
        self.output_schema_as_tool = output_schema_as_tool

        if self.name.lower() != 'retriever':
            self.validate_model()

    def validate_model(self):
        # Useful when using an identical chat model
        if not self.chat_model:
            assert self.model_name, "A model name must be provided (e.g. gpt-4o, gpt-4o-mini)"
            self.chat_model = init_chat_model(model=self.model_name, model_provider=self.model_provider)

        self.validate_schema()
        self.tool_schemas = self.tool_schemas or []
        self.output_schema = self.output_schema or []
        self.tool_schemas.extend(self.output_schema)

        self.chat_model = self.chat_model.bind_tools(self.tool_schemas)

    def validate_node(self):
        """Validate node settings"""
        ...

    def validate_schema(self):
        if not isinstance(self.tool_schemas, list) and self.tool_schemas:
            self.tool_schemas = [self.tool_schemas, ]
        if not isinstance(self.output_schema, list) and self.output_schema:
            self.output_schema = [self.output_schema, ]

    def __call__(
            self,
            state: InputT,
            config: Optional[RunnableConfig] = None,
            context: Optional[ContextT] = None,
            runtime: Runtime = None,
            **kwargs
    ):
        """The abstractive node function receives state input and returns update state
        Subclasses must implement this method

        Args:
            state (Union[InputT, StateT]):
                State only takes the necessary keys declared in InputT from "state_schema" of the graph.
                Default to None
            config (RunnableConfig, optional):
                Config passed during operation.
                Default to None
            context (ContextT, optional):
                Context variables from the program.
                Default to None
            runtime (Runtime, optional):
                Values from runtime.
                Default to None

        Returns:
            Update state
        """
        # -------------------------------
        # -------------------------------
        raise NotImplementedError
