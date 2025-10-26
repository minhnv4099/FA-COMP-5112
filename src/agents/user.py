#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import logging

from langgraph.config import RunnableConfig
from langgraph.graph.state import END
from typing_extensions import override

from ..base.agent import AgentAsNode
from ..base.mapping import register
from ..base.utils import DirectionRouter
from ..utils import InputT

logger = logging.getLogger(__name__)


@register(name='user', type='agent')
class UserAgent(AgentAsNode, node_name="User", use_model=False):
    """
    The User Agent class
    """

    @override
    def __call__(
            self,
            state: InputT | dict,
            runtime: RunnableConfig = None,
            context: RunnableConfig = None,
            config: RunnableConfig = None,
            **kwargs
    ):
        start_message = "-" * 50 + self.name + "-" * 50
        logger.info(start_message)

        user_query = input('Enter a follow-up prompt (now only treat as a string): ')

        if user_query.lower() in ('q', 'quit'):
            next_node = END
            logger.info(f"GOOD BYE!!!")
        else:
            state['queries'] = [user_query]
            state['user_additional_prompt'] = user_query
            state['caller'] = 'user'
            next_node = 'coding'

        end_message = "*" * (100 + len(self.name))
        logger.info(end_message)

        return DirectionRouter.goto(state=state, node=next_node, method='command')
