#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import logging
import os
from json import dumps, loads
from json.decoder import JSONDecodeError
from typing import Union, Generic, Any, Optional, Sequence, Iterable

from langchain.chat_models.base import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.prompt_values import PromptValue
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate
)
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_core.runnables import RunnableConfig
from langchain_core.utils.interactive_env import is_interactive_env
from langchain_openai import ChatOpenAI
from typing_extensions import deprecated

from src.chat_output import DEFAULT_CHAT_OUTPUT_SCHEMA
from src.registry import RegisterChat, fetch_registered
from src.supplier import PROVIDER_TO_ENV, PROVIDER_TO_BASE_URL
from src.types import OutputT, OmegaList, SchemaLike, OmegaDict
from src.utils.decorator import add_note_docstring, must_override
from src.utils.exception import NotOverrideError
from src.utils.file import load_prompt_template_file

logger = logging.getLogger(__name__)

module_path = __name__


@RegisterChat(module_path=module_path, name='base_chat')
class BaseChatAssistance(Generic[OutputT]):
    """The Base Chat Assistance that communicates with user via text chat (conversation)"""

    name: str = None
    """Name of the agent"""

    model_name: str
    """Name of LLM (e.g. ``gpt-4o``, ``gpt-4o-mini``)"""

    model_provider: str
    """Provide of used model (e.g. ``openai``, ``google``, ``openrouter``)"""

    model_api_key: str
    """API key"""

    output_schema: list[Union[dict, OutputT]] | OutputT
    """The structure output the chat model should return"""

    output_schema_as_tool: bool
    """Bind `output_schema` as tool, providing more flexibility. 
    In some cases, the output schema can be bound by ``.with_structure()``"""

    template_file: str
    """File containing message templates, from system to human templates. 
    That are all templates the agent used for its task"""

    # invoke_attempts: int
    # """Attempt to invoke chat model whenever error occur when calling invoke function"""

    # invoke_tries: int
    # """Number of tries invoking"""

    # usage_metadata: dict
    # """Usage metadata"""

    num_input_tokens: int
    """Volume of input tokens passed to chat model"""

    num_output_tokens: int
    """Volume of output tokens chat model generated"""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()

        missing_func = []

        for name, attr in BaseChatAssistance.__dict__.items():
            if getattr(attr, "__must_override__", False):
                if name not in cls.__dict__:
                    missing_func.append(name)

        if missing_func:
            raise NotOverrideError(f"[Warning] Class '{cls.__name__}' didn't override: {missing_func}")

    def __init__(
            self,
            name: str,
            metadata: dict = None,
            output_schema: OutputT = DEFAULT_CHAT_OUTPUT_SCHEMA,
            output_schema_as_tool: bool = None,
            use_model: bool = False,
            model_name: str = None,
            model_provider: str = None,
            model_api_key: str = None,
            chat_model: BaseChatModel = None,
            template_file: str = None,
            **kwargs,
    ):
        # metadata
        self.name = name
        self.metadata = metadata

        # chat model
        self.use_model = use_model
        self.model_name = model_name
        self.model_provider = model_provider
        self.model_api_key = model_api_key
        self.chat_model = chat_model

        # output schema
        self.output_schema = output_schema
        self.output_schema_as_tool = output_schema_as_tool

        # prompt templates
        self.template_file = template_file
        self._prepare_message_templates()
        self._prepare_chat_template()

        # check model
        self._check_model_provider()
        self._check_model_name()
        self._check_chat_model()

        # initialize model + bind schema
        if self.use_model:
            self._initialize_model()
            schemas = self._validate_schemas()
            self._bind_schemas(schemas=schemas)

        # usage metadata
        self.response_metadata = dict()
        self.num_input_tokens = 0
        self.num_output_tokens = 0

        # use as middleware
        self.opening_symbols = "-" * 60 + self.name + "-" * 60
        self.ending_symbols = "*" * (120 + len(self.name))

        self.config = RunnableConfig(
            configurable={"thread_id": self.name},
            recursion_limit=200,
        )

    @deprecated("No needed because can use cheap or free models.")
    def _check_model_name(self):
        ...
        # if self.model_name not in SUPPORTED_MODEL:
        #     raise ValueError(f"We now only support models: {', '.join(SUPPORTED_MODEL)}, but provided '{self.model_name}'")

    def _check_model_provider(self):
        if self.model_provider not in PROVIDER_TO_ENV:
            logger.warning(
                f"Now we only use models from provider: {', '.join(PROVIDER_TO_ENV.keys())}, but provided '{self.model_provider}'"
                f"Use 'openrouter', default")

            self.model_provider = 'openrouter'

    def _check_chat_model(self):
        if self.chat_model is not None:
            logger.critical(f"Now we only accept instantiate `chat_model` from 'model_name'. Pass this value")

    @must_override
    def _prepare_message_templates(self, *args, **kwargs):
        """Prepare message templates for system and human roles.

        This method only works for Chat Assistance with **ONE** system prompt and **ONE** human prompt. \n
        Override it by doing nothing if the chat has other message templates.
        """

        templates_dict = load_prompt_template_file(self.template_file)

        self.system_template = SystemMessagePromptTemplate.from_template(
            template=templates_dict.get('system_template', """"""),
            template_format='f-string',
        )
        self.human_template = HumanMessagePromptTemplate.from_template(
            template=templates_dict.get('human_template', """"""),
            template_format='f-string',
        )

    @must_override
    def _prepare_chat_template(self, system_template=None, human_template=None) -> ChatPromptTemplate:
        """Prepare chat template for a turn

        The method works with the constraints that 1 system template followed by a human template
        """

        if system_template is None:
            _system_template = self.system_template
        else:
            _system_template = system_template

        self.chat_template = ChatPromptTemplate(
            messages=[_system_template, human_template if human_template else self.human_template],
            template_format='f-string',
        )

        return self.chat_template

    def _initialize_model(self):
        """Initialize model based on ``model_name``, ``model_provider``"""

        base_url = PROVIDER_TO_BASE_URL[self.model_provider]

        if self.model_api_key is None:
            api_key = os.getenv(PROVIDER_TO_ENV[self.model_provider])
        else:
            api_key = self.model_api_key

        self.chat_model = ChatOpenAI(
            openai_api_base=base_url,
            model=self.model_name,
            openai_api_key=api_key,
            temperature=0.7,
            rate_limiter=InMemoryRateLimiter(
                requests_per_second=0.1,
                check_every_n_seconds=0.1,
                max_bucket_size=10
            )
        )

    def _convert_to_list(self, seq: Iterable[Any]) -> list[Any]:
        if seq and not isinstance(seq, OmegaList):
            seq = [seq, ]

        return seq or []

    @must_override
    def _validate_schemas(self) -> list[OutputT]:
        """Validate output schemas to chat model"""

        self.output_schema = [
            self.fetch_schema(schema)
            for schema in self._convert_to_list(seq=self.output_schema)
        ]

        return self.output_schema

    def fetch_schema(self, schema: Union[dict, SchemaLike]) -> Union[None, SchemaLike]:
        if not isinstance(schema, OmegaDict):
            return schema

        return fetch_registered(metadata=schema)

    def _bind_schemas(self, schemas):
        """Bind schemas to chat model, and force model to always use the first schema"""

        self.chat_model = self.chat_model.bind_tools(
            tools=schemas,
            # tool_choice=schemas[0]
        )

    @add_note_docstring(docs="Used for 'COMP-5112' project")
    def __call__(
            self,
            input: Union[str, dict, PromptValue],
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
        raise NotImplementedError("Use 'invoke()' to interact with chat.")

    def invoke(
            self,
            input: Union[str, PromptValue, Sequence[BaseMessage]],
            config: Optional[RunnableConfig] = None,
            *,
            stop: Optional[list[str]] = None
    ) -> AIMessage:
        """Invoke chat model with input.

        Returns:
            AIMessage
        """

        ai_message = self.chat_model.invoke(
            input=input,
            config=config if config else self.config,
            stop=stop
        )

        self._count_tokens(ai_message)

        return ai_message

    def _get_pretty_formatted_prompt(self, chat_prompt_template: ChatPromptTemplate, input: dict):
        pretty_input = self._format_input(input=input)

        return chat_prompt_template.invoke(input=pretty_input)

    def _format_input(self, input: dict):
        _inputs = dict()

        for k, v in input.items():
            _inputs[k] = self.get_pretty_prep(v)

        return _inputs

    @classmethod
    def get_pretty_prep(cls, content: str):
        try:
            if isinstance(content, str):
                return dumps(loads(content), indent=4)

            return dumps(content, indent=4)

        except (JSONDecodeError, TypeError) as e:
            return content

    @classmethod
    @deprecated('No longer useful.')
    def create_ai_message(cls, content):
        """Create an ai message based on content user want to view in conversation,
        not raw content or tool call JSON block"""

        return AIMessage(content=content)

    def _get_ai_message_metadata(self, ai_message: AIMessage):
        raise NotImplementedError

    @classmethod
    def get_conversation(cls, messages: Sequence[BaseMessage]):
        conversation = "🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶\n"

        for m in messages:
            conversation += m.pretty_repr(is_interactive_env())
            conversation += '\n'

        conversation += '🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 ' + '\n'

        return conversation.strip()

    @classmethod
    def is_list_of_strings(cls, obj):
        return isinstance(obj, list) and all(isinstance(elem, str) for elem in obj)

    @classmethod
    def log_conversation(cls, _logger, conversation):
        if not cls.is_list_of_strings(conversation) and isinstance(conversation, list):
            conversation = cls.get_conversation(conversation)

        _logger.info(
            f"🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 CONVERSATION 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵\n{conversation}")
        _logger.info(f"🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 ")

    @add_note_docstring(docs="Used for 'COMP-5112' project")
    def _extend_conversation(
            self,
            messages: Sequence[BaseMessage],
            his_conversation: Optional[Sequence[BaseMessage]]
    ):
        """Extend the conversation, getting full one. Used when ``messages`` also contains the system prompt."""

        his_conversation = his_conversation or []

        if his_conversation:
            his_conversation.extend(messages[1:])
        else:
            his_conversation.extend(messages)

        return his_conversation

    def _count_tokens(self, ai_message: AIMessage):
        """Accumulate input and output tokens"""

        usage_metadata = ai_message.usage_metadata
        self.num_input_tokens += usage_metadata['input_tokens']
        self.num_output_tokens += usage_metadata['output_tokens']

    def _used_token_prep(self):
        """Get a string describing input and output token usage"""

        return f'Input tokens: {self.num_input_tokens}, Output tokens: {self.num_output_tokens}'

    def _print_used_tokens(self, _logger):
        """Log input and output token usage"""

        _logger.info(self._used_token_prep())

    def _finish_session(self, _logger, conversation):
        self.log_conversation(_logger, conversation)
        _logger.info(self._used_token_prep())
        _logger.info(self.ending_symbols)
