#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from typing import Union, Generic, Any

from langchain.chat_models.base import BaseChatModel, init_chat_model
from langchain_core.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate, ChatPromptTemplate
from langchain_core.rate_limiters import InMemoryRateLimiter
from langgraph.config import RunnableConfig

from .mapping import register
from ..utils import StateT, InputT, OutputT, ContextT
from ..utils import fetch_schema
from ..utils import load_prompt_template_file


class BaseAgent:
    """The Base Agent class"""
    name: str
    """Unique name of the class"""

    use_model: bool
    """Whether the agent uses model as brain"""


@register(type="agent", name='base')
class AgentAsNode(BaseAgent, Generic[StateT, ContextT, InputT, OutputT]):
    """The Agent As Node class

    An agent has an LLM acting as brain and tools, allowing to interact with external knowledge, environment.
    """

    metadata: dict[str, str] = None
    """Metadata used when attach to a graphs"""

    input_schema: Union[InputT, StateT] = None
    """Input state schema to the node"""

    edges: dict[str, tuple] = None
    """In-coming and out-going edges connected with this node
    ```
    {
        "in_coming" : ('name_node_1', 'name_node_2'),
        "out_going" : ('name_node_3', 'name_node_4')
    }
    ```
    """

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

    def __init_subclass__(cls, name: str = None, use_model: bool = True):
        cls.name = name
        cls.use_model = use_model

    def __init__(
            self,
            metadata: dict = None,
            input_schema: InputT | dict = None,
            edges: dict[str, tuple[str]] = None,
            tool_schemas: list | list[dict] = None,
            output_schema: OutputT | list[OutputT] | list[dict] = None,
            model_name: str = None,
            model_provider: str = None,
            model_api_key: str = None,
            output_schema_as_tool: bool = None,
            chat_model: BaseChatModel = None,
            template_file: str = None,
            **kwargs,
    ):
        self.metadata = metadata
        self.chat_model = chat_model
        self.model_name = model_name
        self.model_provider = model_provider
        self.model_api_key = model_api_key

        self.edges = edges
        self.input_schema = fetch_schema(input_schema)
        self.tool_schemas = tool_schemas
        self.output_schema = output_schema
        self.output_schema_as_tool = output_schema_as_tool

        self.template_file = template_file
        self.system_template = None
        self.human_template = None
        self.chat_template = None

        if self.use_model:
            self.validate_schema()
            self.validate_model()

    def validate_model(self):
        # Useful when using an identical chat model
        import os
        base_url = os.getenv("BASE_URL")
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not self.chat_model:
            assert self.model_name, "A model name must be provided (e.g. gpt-4o, gpt-4o-mini)"
            self.chat_model = init_chat_model(
                model=self.model_name,
                model_provider=self.model_provider,
                base_url=base_url,
                api_key=api_key,
                rate_limiter=InMemoryRateLimiter(
                    requests_per_second=0.1,
                    check_every_n_seconds=0.1,
                    max_bucket_size=10
                ),
            )

        self.chat_model = self.chat_model.bind_tools(self.tool_schemas)

    def validate_node(self):
        """Validate node settings"""
        ...

    def validate_schema(self):
        if self.tool_schemas and not isinstance(self.tool_schemas, list):
            self.tool_schemas = [self.tool_schemas, ]
        if self.output_schema and not isinstance(self.output_schema, list):
            self.output_schema = [self.output_schema, ]

        self.tool_schemas = self.tool_schemas or []
        self.output_schema = self.output_schema or []
        self.tool_schemas.extend(self.output_schema)

        self.tool_schemas = [
            fetch_schema(tool_schema)
            for tool_schema in self.tool_schemas
        ]

    def _prepare_chat_template(self, *args, **kwargs):
        """Prepare ready prompt that would be passed to chat model"""
        templates_dict = load_prompt_template_file(self.template_file)

        self.system_template = SystemMessagePromptTemplate.from_template(
            template=templates_dict.get('system_template', """"""),
            template_format='f-string',
        )
        self.human_template = HumanMessagePromptTemplate.from_template(
            template=templates_dict.get('human_template', """"""),
            template_format='f-string',
        )
        self.chat_template = ChatPromptTemplate(
            messages=[self.system_template, self.human_template],
            template_format='f-string'
        )

    def anchor_call(self, *args, **kwargs):
        """Use this function to generate virtual data that match output schema in reality.
        The main purpose is just test workflow but not call chat model really
        """
        raise NotImplementedError

    def chat_model_call(self, *args, **kwargs):
        """This method actually calls chat model and response follow ``output_schema``"""
        raise NotImplementedError

    def __call__(
            self,
            state: InputT | dict,
            runtime: RunnableConfig = None,
            context: RunnableConfig = None,
            config: RunnableConfig = None,
            **kwargs
    ):
        """The abstractive node function receives state input and returns update state
        Subclasses must implement this method

        Args:
            state (Union[InputT, StateT]):
                State only takes the necessary keys declared in InputT from "state_schema" of the graph.
                Default to None
            config (RunnableConfig, optional):
                Config passed during operation. Default to None
            context (ContextT, optional):
                Context variables from the program. Default to None
            runtime (Runtime, optional):
                Values from runtime. Default to None
        Returns:
            dict: Update state
        """
        # -------------------------------
        raise NotImplementedError
        # -------------------------------
