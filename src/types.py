#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations

from typing import Any, Optional, Union, TYPE_CHECKING
from typing_extensions import Annotated, TypedDict, deprecated, NotRequired, Required
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages

from src.registry import RegisterState, RegisterChatOutputSchema

if TYPE_CHECKING:
    ...


@deprecated('No need')
class RegisterMetadata(TypedDict):
    """Schema used to register any class"""

    type: str
    """Type of the class such as ``chat``, ``agent``, ...."""
    module: str
    """Module (`.py` file) containing the class"""
    name: str
    """The unique name used to register"""


class RegisterFetchMetadata(TypedDict, total=False):
    """Schema used to fetch a class"""

    type: str
    """Type of the class such as ``chat``, ``agent``, ...."""
    name: str
    """The unique name of registered class"""
    kwargs: NotRequired[dict[str, Any]]
    """Additional keywork arguments"""


@RegisterState(module=__name__, name='base_context')
@dataclass(kw_only=True)
class BaseContext:

    user_id: str = field(
        default='1304391',
    )


@RegisterChatOutputSchema(module=__name__, name='base')
class BaseOutput(BaseModel):
    """Always use this schema and its subclasses to format the answers
    This class is an abstractive class for all structured outputs"""

    # content: str = Field(..., description='The content of AI assistance')


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
