#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from typing import Sequence, Literal, Union, Any
from typing_extensions import Annotated, TypedDict

from src.registry import RegisterState
from src.utils import scan_module
from src.types import MutilAgentState

__all__ = scan_module(globals())


@RegisterState(module=__name__, name='planner')
class PlannerState(MutilAgentState):
    """The input state for Planner Agent"""

    task: Annotated[str, ...]
    """Given task provided by user prompt"""


@RegisterState(module=__name__, name='retriever')
class RetrieverState(MutilAgentState):
    """The input state for Retriever Agent"""

    queries: Annotated[Sequence[Union[str, dict[str, str]]], ...]
    """List of queries this agent needs to retrieve relevant document for echo one."""

    coding_task: Annotated[Literal['fix', 'improve', 'generate'], ...]
    """Current task for Coding Agent: *generate script*, *fix error* and *apply improvements*"""


@RegisterState(module=__name__, name='coding')
class CodingState(MutilAgentState):
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


@RegisterState(module=__name__, name='critic')
class CriticState(MutilAgentState):
    """The input state for Critic Agent"""

    current_script: Annotated[Sequence[str], ...]
    """Error-free script after the Initial Creation Phase"""

    validating_prompt: Annotated[str, ...]
    """The pre-defined validating prompt that instruct the model to evaluate objects"""

    task: Annotated[str, ...]
    """The original task given by user"""


@RegisterState(module=__name__, name='verification')
class VerificationState(MutilAgentState):
    """The input state for Verification Agent"""

    current_script: Annotated[str, ...]
    """The script after fixing critic by the coding agent"""

    rendered_images: Annotated[Sequence[str], ...]
    """Sequence of rendered image paths after criticising"""

    critics_solutions: Annotated[dict[int, list[dict[str, str]]], ...]
    """Sequence of critics, (maybe satisfied) and solution"""

    additional_prompt: Annotated[str, ...]
    """Additional prompt provided by user"""


@RegisterState(module=__name__, name='user')
class UserPromptUpState(MutilAgentState):
    """The input state for User Agent"""

    user_additional_prompt: Annotated[Sequence[str], ...]
    """Additional prompts provided by user"""

    current_script: Annotated[str, "The mose recent code"]
    """The mose recent generated script after the first two phases in the process"""

    rendered_images: Annotated[Sequence[str], ...]
    """Sequence of rendered image paths after criticising"""


# TODO: change shared state
@RegisterState(module=__name__, name='shared')
class SharedState(TypedDict):
    """The shared state contains all state channels"""
    planner_state: PlannerState
    retriever_state: RetrieverState
    coding_state: CodingState
    critic_state: CriticState
    verification_state: VerificationState
    user_proxy_state: UserPromptUpState
