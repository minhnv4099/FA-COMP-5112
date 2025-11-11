#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import logging
from typing import Union, Sequence, Optional
from typing_extensions import override, Annotated

from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.prompt_values import PromptValue
from langchain_core.runnables import RunnableConfig

from langgraph.graph import StateGraph
from langgraph.graph import END, START
from langgraph.types import StateSnapshot
from langgraph.runtime import Runtime
from langgraph.checkpoint.memory import InMemorySaver

from src.registry import RegisterChat
from src.base.state import BaseState
from src.base.chat import BaseChatAssistance

logger = logging.getLogger(__name__)


class PersistentChatState(BaseState):

    message: Annotated[str, ...]


@RegisterChat(module_path=__name__, name='persistent_chat')
class PersistentChat(BaseChatAssistance, bypass_override=True, show_5112=False):
    """The Persistent Chat class"""

    state_schema = BaseState
    """State schema"""

    def __init_subclass__(cls, **kwargs):
        ...

    def __init__(
        self,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.graph_builder = StateGraph(
            state_schema=self.state_schema
        )

        self.graph_builder.add_node(
            node='model_call',
            action=self.model_call,
            metadata=None
        )

        self.graph_builder.add_edge(START, 'model_call')
        self.graph_builder.add_edge('model_call', END)

        self.graph = self.graph_builder.compile(checkpointer=InMemorySaver())

    def model_call(
        self,
        state: BaseState,
        runtime: Runtime,
        config: RunnableConfig,
        *args,
        **kwargs
    ):
        """"""
        # logger.info(f"Number of messages: {len(state['messages'])}")
        inputs = state['messages']

        response = super().invoke(input=inputs, config=config)

        return {'messages': response}

    @override
    def invoke(
        self,
        input: Union[str, PromptValue, Sequence[BaseMessage]],
        config: Optional[RunnableConfig] = None,
        *,
        stop: Optional[list[str]] = None
    ) -> AIMessage:
        """"""

        config = config if config else self.config

        self.graph.invoke(
            input={'messages': input},
            config=config
        )

        latest_state = self.get_state(config)

        return latest_state.values['messages'][-1]

    def get_state(self, config: RunnableConfig = None) -> StateSnapshot:
        return self.graph.get_state(config if config else self.config)

    def get_messages(self, config: RunnableConfig = None) -> list[BaseMessage]:
        return self.get_state(config).values['messages']
