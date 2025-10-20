#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from langgraph.config import RunnableConfig
from langgraph.graph.state import END
from typing_extensions import override

from src.base.agent import AgentAsNode
from src.base.mapping import register
from src.base.typing import InputT
from src.base.utils import DirectionRouter


@register(name='user', type='agent')
class UserAgent(AgentAsNode, name="User"):
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
        user_query = input('Enter follow-up prompts: ')

        if user_query.lower() in ('q', 'quit'):
            next_node = END
        else:
            state['queries'] = [user_query]
            state['additional_user_prompts'] = user_query
            next_node = 'coding'

        return DirectionRouter.go_next(state=state, node=next_node, method='command')
