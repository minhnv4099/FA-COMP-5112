#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from typing import Literal
from typing_extensions import Sequence
from pydantic import Field

from src.registry import RegisterChatOutputSchema
from src.utils.decorator import add_note_docstring
from src.utils import scan_module
from src.types import BaseOutput

__all__ = scan_module(globals())


@add_note_docstring(docs="Used for only 'COMP-5112' project")
@RegisterChatOutputSchema(module=__name__, name='planner')
class PlannerOutput(BaseOutput):
    """Because this schema acts as a structured output, always only use this schema when have enough information to
    get the final response. Don't use this schema along with tool calls. This schema contains a sequence of
    manageable subtasks after breaking a task into smaller ones that may be a construction, creation, ... request
    """

    subtasks: Sequence[str] = Field(description="List of smaller manageable subtasks")


@add_note_docstring(docs="Used for only 'COMP-5112' project")
@RegisterChatOutputSchema(module=__name__, name='retriever')
class RetrieverOutput(BaseOutput):
    """Always use this tool to structure your response"""

    summary: str = Field(
        description="Summary of query and retrieved documents.")


@add_note_docstring(docs="Used for only 'COMP-5112' project")
@RegisterChatOutputSchema(module=__name__, name='coding')
class CodingOutput(BaseOutput):
    """Always use this output schema to response user requires generating code"""

    script: str = Field(
        description="Generated script. NOTE: only use 'script' as a key, no any additional prefix or/and suffix character")


@add_note_docstring(docs="Used for only 'COMP-5112' project")
class CriticSolutionPair(BaseOutput):
    """The output schema for a single pair of critic and fix"""

    satisfied: Literal[True, False] = Field(
        description="Verify whether the solution is applied appropriately, True or False")

    critic: str = Field(description="A critic that exists in an image")

    solution: str = Field(description="A solution (action, adjustment) that used by coding agent to "
                                      "modify the script and fix the critic")


@add_note_docstring(docs="Used for only 'COMP-5112' project")
@RegisterChatOutputSchema(module=__name__, name='critic')
class CriticOutput(BaseOutput):
    """Output schema for the critic agent. Always use it"""

    critic_solution_list: Sequence[CriticSolutionPair] = Field(
        description="List of (critic, solution) pairs in the given image")


@add_note_docstring(docs="Used for only 'COMP-5112' project")
class SatisfiedSolution(BaseOutput):
    """Output schema for a single triplet of (satisfied, new_critic, solution)"""

    satisfied: Literal[True, False] = Field(
        description="Verify whether the solution is applied appropriately, True or False")

    new_critic: str = Field(
        description="The new critic/flaw/issuse that need to be solved by 'solution'. It must be 'NONE' if satisfied is True")

    solution: str = Field(
        description="The solution that will be applied to fix the remaining critic. Set 'None' if satisfied = True"
                    "DO NOT use the same value as 'solution' input.")


@add_note_docstring(docs="Used for only 'COMP-5112' project")
@RegisterChatOutputSchema(module=__name__, name='verification')
class VerificationOutput(BaseOutput):
    """Output schema for the verification agent. Always use it"""

    ss_list: Sequence[SatisfiedSolution] = Field(
        examples=[
            {'satisfied': False, 'new_critic': '', 'solution': ''},
            {'satisfied': True, 'new_critic': None, 'solution': ''},
            {'satisfied': False, 'new_critic': '', 'solution': ''}
        ],
        description="The output schema must be either: "
                    "list of dictionary if verify user needs to verify 'critic and solutions' "
                    "OR "
                    "a dictionary if if verify user needs to verify 'prompt'")
