#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import logging

from langchain_core.prompts import ChatPromptTemplate
from langgraph.config import RunnableConfig
from langgraph.types import interrupt
from typing_extensions import override

from src.base.node import AgentAsNode
from src.base.utils import DirectionRouter
from src.registry import RegisterNode, RegisterAgent
from src.types import InputT, OutputT
from src.utils.decorator import add_note_docstring
from src.utils.exception import UserTerminated

logger = logging.getLogger(__name__)


@add_note_docstring(docs="Used for only 'COMP-5112' project")
@RegisterAgent(module_path=__name__, name='user')
@RegisterNode(module_path=__name__, name='user')
class UserAgent(AgentAsNode, node_name="User", use_model=False):
    """The User Agent class"""

    @override
    def __call__(
            self,
            state: InputT | dict,
            runtime: RunnableConfig = None,
            context: RunnableConfig = None,
            config: RunnableConfig = None,
            **kwargs
    ) -> OutputT:
        """"""
        logger.info(self.opening_symbols)
        logger.info('Waiting an additional prompt...')
        if 'verification' in state.get('msg', ""):
            state['msg'] += " Waiting an additional prompt..."
        else:
            state['msg'] = "Waiting an additional prompt..."
        # interrupt graph
        additional_prompt = interrupt(value=state)
        logger.info(f'Additional prompt: {additional_prompt}')

        # terminate the graph
        if additional_prompt in ('q', 'quit'):
            logger.info(f"*************************************** GOOD BYE!!! ***************************************")
            state['msg'] = "User terminated"
            state['additional_prompt'] = None
            raise UserTerminated(state=state)

        else:
            state['queries'] = [additional_prompt, ]
            state['additional_prompt'] = additional_prompt
            state['caller'] = 'user'
            state['coding_task'] = 'improve'
            next_node = 'coding'

        logger.info(self.ending_symbols)

        return DirectionRouter.goto(state=state, node=next_node, method='command')

    @override
    def _prepare_message_templates(self, *args, **kwargs):
        ...

    @override
    def _prepare_chat_template(self, system_template=None, human_template=None) -> ChatPromptTemplate:
        ...
