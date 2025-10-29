#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from typing import Sequence, Literal, Union
from typing_extensions import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from .mapping import register

__all__ = [
    "BaseState",
    "PlannerState",
    "RetrieverState",
    "CodingState",
    "CriticState",
    "VerificationState",
    "UserPromptUpState",
    "SharedState"
]


class BaseState(TypedDict):
    """The base class of state in graphs"""

    id: Annotated[int, ...]
    """ID of that state"""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    """Sequence of messages of ``system``, ``user``, ``assistance``, ``tool``"""


# Agent/Node input states
@register(type='state', name='planner')
class PlannerState(BaseState):
    """The input state for Planner Agent"""

    task: Annotated[str, ...]
    """Given task provided by user prompt"""


@register(type='state', name='retriever')
class RetrieverState(BaseState):
    """The input state for Retriever Agent"""

    queries: Annotated[Sequence[Union[str, dict[str, str]]], ...]
    """List of queries this agent needs to retrieve relevant document for echo one."""

    coding_task: Annotated[Literal['fix', 'improve', 'generate'], ...]
    """Current task for Coding Agent: *generate script*, *fix error* and *apply improvements*"""


@register(type='state', name='coding')
class CodingState(BaseState):
    """The input state for Coding Agent
    The Coding Agent has 2 main responsibilities:
        1. Generate code (until no error)
        2. Apply solutions
    """

    queries: Annotated[list[Union[str, dict]], ...]
    """List of queries
    The queries would be one of 3 types:
        - subtask: list of subtasks (string)
        - error: list of one error (str)
        - critic/satisfied/solution: list of dicts
    """

    has_docs: Annotated[bool, ...]
    """Whether has documents to support coding. If not, call retriever agent to get relevant
    document related to ``queries`` 
    """

    retrieved_docs: Annotated[dict, ...]
    """Dictionary of retrieved documents with key is matching index with query in list
    ``
        {<int>: : <retrieved_docs>}
    ``
    """

    current_script: Annotated[str, ...]
    """The latest script, used to apply fixes(critic), solutions(verification) and errors"""

    previous_scripts: Annotated[Sequence[str], ...,]
    """Previous script when generating code for list of subtasks"""

    coding_task: Annotated[Literal['fix', 'improve', 'generate'], ...]
    """Current task for Coding Agent: *generate script*, *fix error* and *apply improvements*"""

    is_sub_call: Annotated[bool, ...]

    caller: Annotated[str, ...]


@register(type='state', name='critic')
class CriticState(BaseState):
    """The input state for Critic Agent"""

    current_script: Annotated[Sequence[str], ...]
    """Error-free script after the Initial Creation Phase"""

    validating_prompt: Annotated[str, ...]
    """The pre-defined validating prompt that instruct the model to evaluate objects"""

    task: Annotated[str, ...]
    """The original task given by user"""


@register(type='state', name='verification')
class VerificationState(BaseState):
    """The input state for Verification Agent"""

    current_script: Annotated[str, ...]
    """The script after fixing critic by the coding agent"""

    rendered_images: Annotated[Sequence[str], ...]
    """Sequence of rendered image paths after criticising"""

    critics_solutions: Annotated[dict[int, list[dict[str, str]]], ...]
    """Sequence of critics, (maybe satisfied) and solution"""

    additional_prompt: Annotated[str, ...]
    """Additional prompt provided by user"""


@register(type='state', name='user')
class UserPromptUpState(BaseState):
    """The input state for User Agent"""

    user_additional_prompt: Annotated[Sequence[str], ...]
    """Additional prompts provided by user"""

    current_script: Annotated[str, "The mose recent code"]
    """The mose recent generated script after the first two phases in the process"""

    rendered_images: Annotated[Sequence[str], ...]
    """Sequence of rendered image paths after criticising"""


@register(type='state', name='shared')
class SharedState(
    PlannerState,
    RetrieverState,
    CodingState,
    CriticState,
    VerificationState,
    UserPromptUpState,
):
    """The shared state contains all state channels"""
