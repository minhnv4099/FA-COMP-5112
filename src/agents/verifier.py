#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from typing_extensions import override

from src.base.agent import AgentAsNode


class VerificationAgent(AgentAsNode, name='Verification'):
    """
    The Verification Agent class
    """

    @override
    def __call__(self, *args, **kwargs):
        pass
