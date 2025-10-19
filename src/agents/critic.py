#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from typing_extensions import override

from src.base.agent import AgentAsNode


class CriticAgent(AgentAsNode, name='Critic'):
    """
    The Critic Agent class
    """

    @override
    def __call__(self, state, *args, **kwargs):
        ...
