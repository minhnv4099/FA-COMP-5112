#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations

import logging
from typing import (
    Union,
    Sequence,
    Optional,
    TYPE_CHECKING,
    Any,
    Generic,
)
from typing_extensions import override

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.prompt_values import PromptValue
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)

from langgraph.graph import StateGraph
from langgraph.graph import END, START
from langgraph.types import StateSnapshot, RetryPolicy
from langgraph.runtime import Runtime
from langgraph.checkpoint.memory import InMemorySaver

from src.registry import RegisterChat
from src.types import ContextT, StateT
from src.chat.base import BaseChatAssistance
from src.state.base import BaseState
from src.utils.decorator import add_note_docstring, must_override
from src.utils.file import load_prompt_template_file

if TYPE_CHECKING:
    ...

logger = logging.getLogger(__name__)


@RegisterChat(module_path=__name__, name='persistent_chat')
class PersistentChat(
    BaseChatAssistance,
    Generic[StateT, ContextT],
    bypass_override=True, show_5112=False
):
    """The Persistent Chat class"""

    state_schema: type[StateT]
    """State schema"""

    template_file: str
    """File containing message templates, from system to human templates. 
    That are all templates the agent used for its task"""

    system_prompt: SystemMessage = None
    """System prompt"""

    human_template: HumanMessagePromptTemplate = None
    """Human template"""

    def __init_subclass__(cls, **kwargs):
        ...

    def __init__(
        self,
        template_file: str = None,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        # set state schema
        self.state_schema = BaseState

        # prompt templates
        self.template_file = template_file
        if self.template_file:
            self._prepare_message_templates()
            self._prepare_chat_template()

        self.config: RunnableConfig = RunnableConfig(
            recursion_limit=200,
            configurable={
                'thread_id': self.name
            }
        )

        self._build_internal_graph()

        self._set_system_behavior(
            config=self.config,
            system_prompt=self.system_prompt
        )

    def _build_internal_graph(self):
        # TODO: consider using self-defined graph "src/base/graph.py"
        # TODO: add docs
        self.graph_builder = StateGraph[StateT, ContextT, ..., ...](
            state_schema=self.state_schema,
            context_schema=self.state_schema,
            input_schema=self.state_schema,
            output_schema=self.state_schema
        )

        self.graph_builder.add_node(
            node='model_call',
            action=self.model_call,
            retry_policy=RetryPolicy(),
            metadata={
                'description': 'Actually call chat model'
            },
        )

        self.graph_builder.add_edge(START, 'model_call')
        self.graph_builder.add_edge('model_call', END)

        self.graph = self.graph_builder.compile(
            checkpointer=InMemorySaver(),
            name=self.name
        )

    @add_note_docstring('A single node of internal graph')
    def model_call(
        self,
        state: Any,
        config: Optional[RunnableConfig] = None,
        *,
        runtime: Optional[Runtime[ContextT]] = None,
        **kwargs
    ):
        # TODO: add docs
        """"""
        # logger.info(f"Number of messages: {len(state['messages'])}")
        response = self.internal_invoke(
            input=state['messages'],
            config=config
        )

        return {'messages': response}

    @override
    def invoke(
        self,
        input: Union[str, PromptValue, Sequence[BaseMessage]],
        config: Optional[Union[RunnableConfig, dict]] = None,
        *,
        context: Optional[Runtime[ContextT]] = None,
        **kwargs,
    ) -> BaseMessage:
        # TODO: add docs
        """"""
        config = config if config else self.config

        self.graph.invoke(
            input={'messages': input},
            config=config,
            context=context
        )

        return self.get_messages(config)[-1]

    @add_note_docstring('COMP-5112 project')
    @must_override
    def _prepare_message_templates(self, *args, **kwargs):
        """Prepare message templates for system and human roles.

        This method only works for Chat Assistance with **ONE** system prompt and **ONE** human prompt. \n
        Override it by doing nothing if the chat has other message templates.
        """

        templates_dict = load_prompt_template_file(self.template_file)

        self.system_prompt = SystemMessage(
            content=templates_dict.get('system_template', """"""),
        )
        self.human_template = HumanMessagePromptTemplate.from_template(
            template=templates_dict.get('human_template', """"""),
            template_format='f-string',
        )

    @add_note_docstring('COMP-5112 project')
    @must_override
    def _prepare_chat_template(self, system_template=None, human_template=None) -> ChatPromptTemplate:
        """Prepare chat template for a turn

        The method works with the constraints that 1 system template followed by a human template
        """

        if system_template is None:
            _system_template = self.system_prompt
        else:
            _system_template = system_template

        self.chat_template = ChatPromptTemplate(
            messages=[_system_template, human_template if human_template else self.human_template],
            template_format='f-string',
        )

        return self.chat_template

    def _set_system_behavior(
        self,
        config: Optional[Union[RunnableConfig, dict]],
        system_prompt: Optional[Union[SystemMessage, str]] = None
    ):
        if not system_prompt:
            system_prompt = SystemMessage(content="You are a very helpful assistance.")
        elif isinstance(system_prompt, str):
            system_prompt = SystemMessage(content=system_prompt)

        self.put_state(
            config=config,
            values={
                'messages': [system_prompt, ]
            }
        )

    def put_state(
        self,
        config: Optional[Union[RunnableConfig, dict]],
        values: dict
    ):
        self.graph.update_state(
            config=config,
            values=values
        )

    def get_state(
        self,
        config: Optional[Union[RunnableConfig, dict]] = None
    ) -> StateSnapshot:
        return self.graph.get_state(config if config else self.config)

    def get_messages(
        self,
        config: Optional[Union[RunnableConfig, dict]] = None
    ) -> list[BaseMessage]:
        return self.get_state(config).values.get('messages', [])

    def print_conversation(
        self,
        config: Optional[Union[RunnableConfig, dict]] = None
    ):
        for m in self.get_messages(config):
            m.pretty_print()
