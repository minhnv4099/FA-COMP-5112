#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from typing import Union, Literal

from langgraph.types import Command, Send


class DirectionRouter:
    """This class acts as a direction router base on 'Command' or 'Send' mechanism"""

    @classmethod
    def goto(
            cls,
            state: dict,
            node: str,
            method: Literal['command', 'send'] = 'command'
    ) -> Union[Command, Send, None]:
        if method.lower() == 'command':
            return Command(update=state, goto=node)
        elif method.lower() == 'send':
            return Send(arg=state, node=node)
        return None
