#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import logging
from typing import Generic, Optional, TYPE_CHECKING, Union

from langchain_core.messages import SystemMessage
from typing_extensions import override, Literal

from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate
from langgraph.config import RunnableConfig
from langgraph.runtime import Runtime
from langgraph.types import interrupt, Command

from src.registry import RegisterNode, RegisterAgent
from src.typing import StateT, ContextT, InputT, OutputT
from src.utils import DirectionRouter
from src.node.base import BaseNode
from src.utils.decorator import add_note_docstring
from src.utils.exception import UserTerminated

if TYPE_CHECKING:
    ...

logger = logging.getLogger(__name__)


@add_note_docstring(docs="Used for only 'COMP-5112' project")
@RegisterAgent(module=__name__, name='user')
@RegisterNode(module=__name__, name='user')
class UserAgent(
    BaseNode,
    Generic[StateT, ContextT, InputT, OutputT],
    node_name="User",
    use_model=False
):
    """The User Agent class"""

    @override
    def __call__(
        self,
        state: StateT,
        config: Optional[RunnableConfig] = None,
        *,
        runtime: Optional[Runtime[ContextT]] = None,
        **kwargs
    ) -> Command[Literal['coding', '__end__']]:
        """"""
        additional_prompt = interrupt(value="Enter additional prompt...")

        logger.info(self.opening_symbols)
        logger.info(f'Additional prompt: {additional_prompt}')

        next_node: Literal['__end__', 'coding']
        # terminate the graph
        if additional_prompt in ('q', 'quit'):
            next_node = '__end__'
            logger.info(f"*************************************** GOOD BYE!!! ***************************************")
            state['msg'] = "User terminated"
            state['additional_prompt'] = None

        else:
            state['agent_response'] = [additional_prompt, ]
            state['additional_prompt'] = additional_prompt
            state['caller'] = 'user'
            state['coding_task'] = 'improve'
            next_node = 'coding'

        logger.info(self.closing_symbols)

        return DirectionRouter.jump(
            updates=state,
            jump_to=next_node,
            method='command'
        )

    @override
    def _prepare_message_templates(self, *args, **kwargs):
        ...

    @override
    def _prepare_chat_template(self, system_template=None, human_template=None) -> ChatPromptTemplate:
        ...

    @override
    def _set_system_behavior(
        self,
        config: Optional[Union[RunnableConfig, dict]],
        system_prompt: Optional[Union[SystemMessage, SystemMessagePromptTemplate, str]] = None,
        sys_kwargs: Optional[dict[str, str]] = None
    ):
        ...
