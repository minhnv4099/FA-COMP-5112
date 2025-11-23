#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from typing import Any
from typing_extensions import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from src.utils import scan_module

__all__ = scan_module(globals())


class BaseState(TypedDict):
    """The base class of state in graphs"""

    id: Annotated[int, ...]
    """ID of that state"""

    messages: Annotated[list[BaseMessage],  add_messages]
    """Sequence of messages of ``system``, ``user``, ``ai``, ``tool``, ``parser``"""


class MutilAgentState(BaseState):
    """The state class for multi-agent systems"""

    agent_response: Annotated[Any, ...]
    """"""

    caller: Annotated[str, ...]
    """The agent just called"""
