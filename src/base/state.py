#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from typing import Sequence, Literal, Union

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, TypedDict

from .mapping import register

__all__ = [
    "BaseState",
    "PlannerState",
    "RetrieverState",
    "CodingState",
    "CriticState",
    "VerificationState",
    "UserPromptUpState",
    "IcpOverallState",
    "IcpInputState",
    "IcpOutputState",
    "ArpOverallState",
    "ArpInputState",
    "ArpOutputState",
    "UrpOverallState",
    "UrpInputState",
    "UrpOutputState"
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

    queries: Annotated[Sequence[str], ...]
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
        - subtask: subtasks provided by planner agent
        - error: error when execute script
        - improvements: provided by critic or verification agents
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

    # error: Annotated[str, "The yielded command when executing the script"]
    # """Errors that were produced when executing the script"""

    # current_subtask: Annotated[str, ...]
    # """Current subtask coding agent are working on"""
    #
    # code_snippet: Annotated[str, ...]
    # """Retrieved documents associated with `current subtask`"""
    #
    # previous_scripts: Annotated[list[str], ...]
    # """List of generated code of previous subtasks, helping model understand and be able to
    # point out connecting points between scripts/subtasks"""


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

    rendered_images: Annotated[Sequence[str], ...]
    """Sequence of rendered image paths after criticising"""

    critic_and_fixes: Annotated[list[list[str]], ...]
    """Sequence of critics and fixes provided by the `critic agent`"""


@register(type='state', name='user')
class UserPromptUpState(BaseState):
    """The input state for User Agent"""

    follow_up_prompts: Annotated[Sequence[str], ...]
    """Additional prompts provided by user"""

    current_code: Annotated[str, "The mose recent code"]
    """The mose recent generated script after the first two phases in the process"""

    terminated: Annotated[bool, ...]
    """Whether user terminates the process"""


# Phase/Subgraph input states
class IcpInputState(PlannerState, RetrieverState, CodingState):
    """The input schema for the Initial Creation Phase"""


class IcpOutputState(BaseState):
    """The output schema of the Initial Creation Phase"""

    error_free_code: Annotated[str, ...]
    """The generated code without yielding any error"""


class IcpOverallState(IcpInputState, IcpOutputState):
    """The state schema of the Initial Creation Phase"""


class ArpInputState(IcpOutputState):
    """The input schema of the Auto Refinement Phase"""


class ArpOutputState(BaseState):
    """The output schema of the Auto Refinement Phase"""

    refined_code: Annotated[str, ...]
    """The script after being refined by critic and verification agents"""


class ArpOverallState(ArpInputState, ArpOutputState):
    """The state schema of the Auto Refinement Phase"""


class UrpInputState(ArpOutputState):
    """The input schema of the User-guided Refinement Phase"""


class UrpOutputState(BaseState):
    """The output schema of the User-guided Refinement Phase"""

    user_guided_code: Annotated[str, ...]
    """The script after the last phase"""


class UrpOverallState(ArpInputState, ArpOutputState):
    """The state schema of the User-guided Refinement Phase"""


# Share state
@register(name='shared', type='state')
class SharedState(PlannerState, RetrieverState, CodingState, CriticState):
    """The shared state contains all state channels"""
