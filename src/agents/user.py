#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import logging
from typing_extensions import override

from langgraph.config import RunnableConfig
from langgraph.types import interrupt
from langgraph.graph.state import END

from ..base.agent import AgentAsNode
from ..base.mapping import register
from ..base.utils import DirectionRouter
from ..utils.types import InputT
from ..utils.exception import UserTerminated

logger = logging.getLogger(__name__)


@register(name='user', type='agent')
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
    ):
        logger.info(self.opening_symbols)

        logger.info('Waiting an additional prompt...')
        additional_prompt = interrupt(value={'state': state, 'request': "Enter follow-up prompt"})
        logger.info(f'Additional prompt: {additional_prompt}')

        if additional_prompt in ('q', 'quit'):
            next_node = END
            logger.info(f"*************************************** GOOD BYE!!! ***************************************")
            raise UserTerminated(state=state, msg="User terminated")

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
