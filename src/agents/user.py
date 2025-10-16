#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from typing_extensions import override

from src.base.agent import AgentAsNode


class UserAgent(AgentAsNode, name="User"):
    """
    The User Agent class
    """

    @override
    def __call__(self, *args, **kwargs):
        pass
