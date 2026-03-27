#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
"""Base chat acts as an LLM"""

from __future__ import annotations

import os
import logging
from typing import (
    Any,
    Union,
    Optional,
    Sequence,
    TYPE_CHECKING,
    final
)

from langchain_core.prompt_values import PromptValue
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import (
    BaseMessage,
    SystemMessage,
    AIMessage,
    HumanMessage
)
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain_openai import ChatOpenAI

from src.registry import RegisterChat
from src.supplier import PROVIDER_TO_ENV, PROVIDER_TO_BASE_URL
from src.chat.mixin import TokenCountMixin
from src.utils.decorator import add_note_docstring, must_override
from src.utils.file import load_prompt_template_file
from src.utils.exception import EmptyMessage, InvalidInput

if TYPE_CHECKING:
    from langchain.chat_models.base import BaseChatModel

logger = logging.getLogger(__name__)

LanguageModelInput = Union[str, dict[str, Any], PromptValue, BaseMessage, Sequence[BaseMessage], list[BaseMessage]]
_DEFAULT_MODEL_NAME = "meta-llama/llama-3.3-70b-instruct:free"
_DEFAULT_MODEL_PROVIDER = "openrouter"


@RegisterChat(module=__name__, name='base_chat')
class BaseChat(TokenCountMixin):
    """The Base Chat class acting as an LLM, receiving a prompt and generate one response."""

    name: str
    """Name of the chat."""

    metadata: dict
    """Metadata."""

    model_name: str
    """Name of LLM (e.g. ``gpt-4o``, ``gpt-4o-mini``, `etc.`)."""

    model_provider: str
    """Provide of used model (e.g. ``openai``, ``google``, ``openrouter``)."""

    endpoint_url: str = None
    """The endpoint url. Can be used to initialize chat model outside."""

    model_api_key: str = None
    """API key. It can be load from environment variables based on provider.
    
    Can be used to initialize chat model outside.
    """

    chat_model: Union[BaseChat, BaseChatModel, None]
    """Accept chat model instance of ``BaseChat`` (itself) or ``BaseChatModel``."""

    template_file: str
    """File containing message templates, from system to human templates.
    
    This file should be `.yaml` file with 2 typically keys:
        - system_template
        - human_template
    that will be loaded automatically.
    """

    system_template: SystemMessagePromptTemplate = None
    """System prompt."""

    human_template: HumanMessagePromptTemplate = None
    """Human template."""

    chat_template: ChatPromptTemplate = None
    """Template chat consists system and human messages."""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()

    def __init__(
        self,
        name: Optional[str] = None,
        metadata: Optional[dict] = None,
        use_model: bool = True,
        model_name: Optional[str] = None,
        model_provider: Optional[str] = None,
        model_api_key: Optional[str] = None,
        chat_model:  Union[BaseChat, BaseChatModel, None] = None,
        llm_engine: Union[BaseChat, BaseChatModel, None] = None,
        template_file: Optional[str] = None,
        *args,
        **kwargs,
    ):
        """"""
        self.name = name if name else repr(self.__class__.__name__)
        self.metadata = metadata

        # chat model
        self.use_model = use_model
        self.model_api_key = model_api_key

        # check model
        if self.use_model:
            self.chat_model = self.validate_chat_model(llm_engine or chat_model)
            if self.chat_model is None:
                # initialize model
                self.model_provider = self.validate_model_provider(model_provider)
                self.model_name = self.validate_model_name(model_name)
                self.chat_model = self._initialize_model()

        # prompt templates
        self.template_file = template_file
        self._prepare_message_templates()
        self.chat_template = self._prepare_chat_template()

    # TODO: move to llm engine
    @classmethod
    def validate_chat_model(cls, chat_model: Union[BaseChat, BaseChatModel]):
        """Validate chat model. The given model can be either ``BaseChat`` (Langrework) or ``BaseChatModel`` (Langchain).

        Args:
            chat_model: Chat model.

        Returns:
            Given chat model if it is valid, else None.
        """
        if chat_model is not None:
            if isinstance(chat_model, BaseChat):
                if chat_model.__class__ is not BaseChat:
                    msg = (
                        f"[CRITICAL]-Now we only accept chat_model of BaseChat class, not subclasses, but got {chat_model.__class__!r}. "
                        f"Chat model (BaseChat) acts as an LLM engine, {chat_model.__class__.__name__!r} may have some capabilities beyond a LLM. "
                        f"So instantiating from ``model_name`` instead.")
                    chat_model = None
                else:
                    msg = f"Use pre-defined chat {repr(chat_model.__class__)!r} with llm {chat_model.model_name!r}"
                    chat_model = chat_model.llm_engine
            else:
                msg = f"Use pre-defined chat {repr(chat_model.__class__)!r}."
                chat_model = chat_model

        else:
            msg = f"Instantiate chat model from model name and model provider."
            chat_model = None

        logger.info(msg)
        return chat_model

    # TODO: move to llm engine
    @classmethod
    def validate_model_name(cls, model_name: str) -> str | None:
        """Validate model name.

        Args:
            model_name: Name of model (`gpt-4o-mini`, ...).

        Returns:
            Given model name if valid, else None.
        """
        if not model_name:
            logger.critical(f"Invalid model name: {model_name!r}. Use {_DEFAULT_MODEL_NAME!r} by default.")
            return _DEFAULT_MODEL_NAME

        return model_name

    # TODO: move to llm engine
    @classmethod
    def validate_model_provider(cls, model_provider: str) -> str | None:
        """Validate model provider.
        Now we only support ``openrouter`` provider.

        Args:
            model_provider: Name of model provider (`openrouter`, `openai`, `google`, ...).

        Returns:
            Given provider name if it is valid, else None.
        """
        if model_provider not in PROVIDER_TO_ENV:
            supported_provider = ', '.join(filter(lambda x: x, PROVIDER_TO_ENV.keys()))
            logger.warning(
                f"Now we only use models from provider: {supported_provider!r}, but got {model_provider!r}. "
                f"Use {_DEFAULT_MODEL_PROVIDER!r} by default")
            return _DEFAULT_MODEL_PROVIDER

        return model_provider

    # TODO: move to llm engine
    def _initialize_model(self, **chat_kwargs):
        """Initialize model based on ``model_name``, ``model_provider``.

        Args:
            chat_kwargs: Keywork arguments for chat model (`temperature`, `max_tokens`, ...).

        Returns:
            Chat model from ``ChatOpenAI``.
        """
        return ChatOpenAI(
            model=self.model_name,
            openai_api_base=self.base_url,  # type: ignore
            openai_api_key=self.api_key,  # type: ignore
            temperature=chat_kwargs.get("temperature", 0.7),
            max_tokens=chat_kwargs.get("max_tokens", 2000),
            streaming=False,
            disable_streaming=True,
            rate_limiter=InMemoryRateLimiter(
                requests_per_second=0.1,
                check_every_n_seconds=0.1,
                max_bucket_size=10
            ),
        )

    # TODO: move to llm engine
    @property
    def api_key(self):
        """The API key."""
        if not self.model_api_key:
            self.model_api_key = os.getenv(PROVIDER_TO_ENV[self.model_provider])

        return self.model_api_key

    # TODO: move to llm engine
    @property
    def base_url(self):
        """The endpoint url."""
        if not self.endpoint_url:
            self.endpoint_url = PROVIDER_TO_BASE_URL[self.model_provider]

        return self.endpoint_url

    @property
    def llm_engine(self):
        """Chat model exposed as an LLM engine."""
        return self.chat_model

    @must_override
    def __call__(
        self,
        *args,
        **kwargs
    ):
        """"""
        raise NotImplementedError("Use 'invoke()' to interact with chat.")

    def validate_input(self, input: LanguageModelInput) -> LanguageModelInput:
        """Validate input before pass to LLM.

        Raises:
            EmptyMessage: If the human message is empty.
            InvalidInput: If the input is different from desired types.
        """
        if isinstance(input, str):
            if len(input) == 0:
                raise EmptyMessage('Error: Input must have at least 1 token')
            return self.chat_template.invoke(input={'message': input})
        elif isinstance(input, dict):
            return self.chat_template.invoke(input=input)
        elif isinstance(input, (PromptValue, BaseMessage, Sequence, list)):
            return input
        else:
            msg = f"Expect type {repr(LanguageModelInput)!r}, but got {type(input)!r}"
            raise InvalidInput(msg)

    def invoke(
        self,
        input: LanguageModelInput,
        config: Optional[Union[RunnableConfig, dict]] = None,
        *,
        stop: Optional[list[str]] = None
    ) -> AIMessage:
        """The invocation function exposed to users.

        Args:
            input: Input fed to the chat model.
                Types:

                - ``str``: Content of the human message in chat template.
                - ``dict``: To format ``chat_template``, all keys must be valid.
                - ``PromptValue, BaseMessage, Sequence[BaseMessage]``: Pass directly.
            config: (deprecated) Config to separate streams of conversation. It's only useful when using with persistent chat.
            stop: The sequence of string the model needs to stop generating if encounter

        Returns:
            The generated response.
        """
        try:
            input = self.validate_input(input)
        except (EmptyMessage, InvalidInput) as e:
            return AIMessage(content=str(e))

        return self.internal_invoke(
            input=input,
            config=config,
            stop=stop
        )

    @final
    def internal_invoke(
        self,
        input: LanguageModelInput,
        config: Optional[Union[RunnableConfig, dict]] = None,
        *,
        stop: Optional[list[str]] = None
    ) -> AIMessage:
        """Internally invoke chat model with input to get response.

        Present exposing this method outside, only called inside.

        Args:
            input: Input fed to the chat model
            config: Config to separate streams of conversation. It's only useful when using with persistent chat.
            stop: The sequence of string the model needs to stop generating if encounter

        Returns:
            The generated response.
        """
        ai_message = self.llm_engine.invoke(
            input=input,
            config=config,
            stop=stop
        )
        self._count_tokens(ai_message)

        return ai_message

    def _prepare_message_templates(self, *args, **kwargs):
        """Prepare message templates for system and human roles by loading templates from ``template_file``.

        This method only works for Chat Assistance with **ONE** system prompt and **ONE** human prompt. \n
        Override it by doing nothing if the chat has other message templates.
        """
        templates = load_prompt_template_file(self.template_file)

        if isinstance(templates, str):
            templates_dict = {
                "system_template": templates,
                "human_template": """{message}"""
            }
        else:
            templates_dict = templates

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
    def _prepare_chat_template(
        self,
        system_template: Optional[SystemMessagePromptTemplate | SystemMessage] = None,
        human_template: Optional[HumanMessagePromptTemplate | HumanMessage | str] = None,
    ) -> ChatPromptTemplate:
        """Prepare chat template for every call turn.

        The method works with the constraints that 1 system template followed by a human template

        Args:
            system_template: System template with input variables or system message.
            human_template: Human template with input variables or human message.

        Returns:
            Template with system and human template ready to format all input variables.
        """
        return ChatPromptTemplate(
            messages=[
                system_template if system_template else self.system_template,
                human_template if human_template else self.human_template
            ],
            template_format='f-string',
        )
