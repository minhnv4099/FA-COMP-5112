#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from pydantic import BaseModel, Field
from typing_extensions import Sequence

from .mapping import register

__all__ = [
    "BaseOutput",
    "PlannerOutput",
    "RetrieverOutput",
    "CodingOutput",
    "CriticOutput",
    "VerificationOutput",
]


class BaseOutput(BaseModel):
    """Always use this schema and its subclasses to format the answers
    This class is an abstractive class for all structured outputs in the graph"""


@register(type='structured_output', name='planner')
class PlannerOutput(BaseOutput):
    """Always use this schema whenever returning final response
    Given a task such create a 3d chair, break it into smaller ones [create legs, backseat, backrest, ...]"""

    subtasks: Sequence[str] = Field(description="List of smaller subtasks after breaking a big task")


@register(type='structured_output', name='retriever')
class RetrieverOutput(BaseOutput):
    """Always use this tool to structure your response"""

    summary: str = Field(
        description="Summary of query and retrieved documents.")


@register(type='structured_output', name='coding')
class CodingOutput(BaseOutput):
    """Always use this output schema to response when generating code"""

    script: str = Field(
        description="Generated script. NOTE: only use 'script' as a key, no any additional prefix or/and suffix character")


class CriticFixPair(BaseOutput):
    """The output schema for a single pair of critic and fix"""

    critic: str = Field(description="A critic that exists in an image")

    fix: str = Field(description="A fix (action, adjustment) that used by coding agent to "
                                 "modify the script and fix the critic")


@register(type='structured_output', name='critic')
class CriticOutput(BaseOutput):
    """Output schema for the critic agent"""

    critic_fix_list: Sequence[CriticFixPair] = Field(
        description="List of (critic, fix) pairs in the given image")


class CriticSatisfiedSolution(BaseOutput):
    """The schema used to response whether the solution/fix is applied to solve each item critic and fix"""

    critic: str = Field(description="A critic that exists in an image pointed out by the critic agent")

    satisfied: str = Field(description="Whether the critic is solve appropriately. "
                                       "Set value 'YES' if it solved, otherwise 'PARTIAL' along with detected critic.")

    solution: str = Field(description="The solution that will be applied to solve existing critics.")


@register(type='structured_output', name='verification')
class VerificationOutput(BaseOutput):
    """Output schema for the verification agent"""

    css_list: Sequence[CriticSatisfiedSolution] = Field(
        description="The list of tuples of (critic, satisfied, solution)")
