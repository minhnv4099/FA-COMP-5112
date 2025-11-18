#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
"""Base chat acts as an LLM"""

from __future__ import annotations

import os
import logging
from typing import (
    Union,
    Optional,
    Sequence,
    TYPE_CHECKING
)
from typing_extensions import deprecated

from langchain_core.prompt_values import PromptValue
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import BaseMessage, SystemMessage, AIMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain_openai import ChatOpenAI

from src.registry import RegisterChat
from src.supplier import PROVIDER_TO_ENV, PROVIDER_TO_BASE_URL
from src.chat.mixin import ChatMixin
from src.utils.decorator import add_note_docstring, must_override
from src.utils.exception import NotOverrideError
from src.utils.file import load_prompt_template_file

if TYPE_CHECKING:
    from langchain.chat_models.base import BaseChatModel

logger = logging.getLogger(__name__)


@RegisterChat(module_path=__name__, name='base_chat')
class BaseChat(ChatMixin):
    """The Base Chat class acting as an LLM"""

    name: str
    """Name of the chatbot"""

    metadata: dict
    """Metadata"""

    model_name: str
    """Name of LLM (e.g. ``gpt-4o``, ``gpt-4o-mini``)"""

    model_provider: str
    """Provide of used model (e.g. ``openai``, ``google``, ``openrouter``)"""

    endpoint_url: str
    """The endpoint url. Can be used to initialize chat model outside"""

    model_api_key: str
    """API key. It can be load from environment variables based on provider.
    Can be used to initialize chat model outside
    """

    template_file: str
    """File containing message templates, from system to human templates. 
    That are all templates the agent used for its task"""

    system_template: Union[SystemMessagePromptTemplate, SystemMessage] = None
    """System prompt"""

    human_template: HumanMessagePromptTemplate = None
    """Human template"""

    chat_template: ChatPromptTemplate = None
    """Template chat consists system and human messages"""

    num_input_tokens: int
    """Volume of input tokens passed to chat model"""

    num_output_tokens: int
    """Volume of output tokens chat model generated"""

    opening_symbols: str

    ending_symbols: str

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()

        missing_func = []
        comp_5112_func = []

        for name, attr in BaseChat.__dict__.items():
            if getattr(attr, "__must_override__", False):
                if name not in cls.__dict__:
                    missing_func.append(name)

            if getattr(attr, "__note_docstring__", False):
                if "5112" in attr.__note_docstring__:
                    comp_5112_func.append(name)

        if kwargs.get('show_5112', False):
            if comp_5112_func:
                logger.warning(f'{comp_5112_func} are used only for "COMP-5112" project. '
                               f'Only use them in the project scope.')

        if not kwargs.get('bypass_override', True):
            if missing_func:
                raise NotOverrideError(f"[Warning] Class '{cls.__name__}' didn't override: {missing_func}")

    def __init__(
        self,
        name: str = None,
        metadata: dict = None,
        use_model: bool = True,
        model_name: str = None,
        model_provider: str = None,
        model_api_key: str = None,
        chat_model: BaseChatModel = None,
        template_file: str = None,
        **kwargs,
    ):
        """"""
        # metadata
        self.name = name if name else self.__class__
        self.metadata = metadata

        # chat model
        self.use_model = use_model
        self.model_name = model_name
        self.model_provider = model_provider
        self.model_api_key = model_api_key
        self.chat_model = chat_model

        # check model
        self._check_model_provider()
        self._check_model_name()
        self._check_chat_model()

        # initialize model
        if self.use_model:
            self._initialize_model()

        # prompt templates
        self.template_file = template_file
        self._prepare_message_templates()
        self._prepare_chat_template()

        # usage metadata
        self.num_input_tokens = 0
        self.num_output_tokens = 0

        # use as middleware
        self.opening_symbols = "-" * 60 + ' ' + self.name + ' ' + "-" * 60
        self.ending_symbols = "*" * (122 + len(self.name))

    @deprecated("No needed because can use cheap or free models.")
    def _check_model_name(self):
        ...

    def _check_model_provider(self):
        if self.model_provider not in PROVIDER_TO_ENV:
            supported_provider = ', '.join(filter(lambda x: x, PROVIDER_TO_ENV.keys()))
            logger.warning(
                f"Now we only use models from provider: {supported_provider}, but got '{self.model_provider}'"
                f"Use 'openrouter', default")
            self.model_provider = 'openrouter'

    def _check_chat_model(self):
        if self.chat_model is not None:
            logger.critical(f"Now we only accept instantiating `chat_model` from 'model_name'. Pass this value")

    def _initialize_model(self):
        """Initialize model based on ``model_name``, ``model_provider``"""

        self.endpoint_url = PROVIDER_TO_BASE_URL[self.model_provider]

        if self.model_api_key is None:
            self.model_api_key = os.getenv(PROVIDER_TO_ENV[self.model_provider])

        self.chat_model = ChatOpenAI(
            model=self.model_name,
            openai_api_base=self.endpoint_url,  # type: ignore
            openai_api_key=self.model_api_key,  # type: ignore
            temperature=0.7,
            rate_limiter=InMemoryRateLimiter(
                requests_per_second=0.1,
                check_every_n_seconds=0.1,
                max_bucket_size=10
            ),
        )

    @property
    def api_key(self):
        return self.model_api_key

    @property
    def base_url(self):
        return self.endpoint_url

    @add_note_docstring(docs="Used for 'COMP-5112' project")
    def __call__(
        self,
        *args,
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

    def internal_invoke(
        self,
        input: Union[str, PromptValue, Sequence[BaseMessage]],
        config: Optional[Union[RunnableConfig, dict]] = None,
        *,
        stop: Optional[list[str]] = None
    ) -> AIMessage:
        """Internally invoke chat model with input to get response.
        Present exposing this method outside, only called by other operations/

        Args:
            input:
                Input fed to the chat model
            config:
                Config to separate streams of conversation. It's only useful when using with persistent chat.
            stop:
                The sequence of string the model needs to stop generating if encounter

        Returns:
            The generated response.
        """
        if len(input) == 0:
            return AIMessage(content='Error: Input must have at least 1 token')

        ai_message = self.chat_model.invoke(
            input=input,
            config=config,
            stop=stop
        )
        self._count_tokens(ai_message)

        return ai_message

    def invoke(
        self,
        input: Union[str, PromptValue, Sequence[BaseMessage]],
        config: Optional[Union[RunnableConfig, dict]] = None,
        *,
        stop: Optional[list[str]] = None
    ) -> AIMessage:
        """The invocation function exposed to user

        Args:
            input:
                Input fed to the chat model
            config:
                Config to separate streams of conversation. It's only useful when using with persistent chat.
            stop:
                The sequence of string the model needs to stop generating if encounter

        Returns:
            The generated response.
        """
        # TODO: process invoke chat template when different keys
        prompt = self.chat_template.invoke(
            input={'message': input},
            config=config
        )
        return self.internal_invoke(
            input=prompt,
            config=config,
            stop=stop
        )

    @must_override
    def _prepare_message_templates(self, *args, **kwargs):
        """Prepare message templates for system and human roles.

        This method only works for Chat Assistance with **ONE** system prompt and **ONE** human prompt. \n
        Override it by doing nothing if the chat has other message templates.
        """
        templates_dict = load_prompt_template_file(self.template_file)

        self.system_template = SystemMessagePromptTemplate.from_template(
            template=templates_dict.get(
                'system_template',
                "You are a very helpful assistance."
            ),
            template_format='f-string'
        )
        self.human_template = HumanMessagePromptTemplate.from_template(
            template=templates_dict.get('human_template', """{message}"""),
            template_format='f-string',
        )

    @add_note_docstring('Prepare dynamic prompt')
    @must_override
    def _prepare_chat_template(
        self,
        system_prompt: Optional[SystemMessagePromptTemplate, SystemMessage] = None,
        human_template: Optional[HumanMessagePromptTemplate] = None,
    ):
        """Prepare chat template for a turn

        The method works with the constraints that 1 system template followed by a human template
        """
        self.chat_template = ChatPromptTemplate(
            messages=[
                system_prompt if system_prompt else self.system_template,
                human_template if human_template else self.human_template
            ],
            template_format='f-string',
        )
