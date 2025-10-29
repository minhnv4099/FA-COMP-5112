#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from pydantic import BaseModel, Field
from typing import Union, Literal
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

    solution: str = Field(description="A solution (action, adjustment) that used by coding agent to "
                                      "modify the script and fix the critic")


@register(type='structured_output', name='critic')
class CriticOutput(BaseOutput):
    """Output schema for the critic agent"""

    critic_solution_list: Sequence[CriticFixPair] = Field(
        description="List of (critic, solution) pairs in the given image")


class ChangeSatisfiedSolution(BaseOutput):
    """Always use this schema when user needs to verify the 'change'"""

    # change: str = Field(description="An additional prompt provided by user. Always use the same value as input")

    satisfied: Literal[True, False] = Field(
        description="Indicator whether the change is applied appropriately, True or False")
    # "If the critic was not solved, set 'PARTIAL' and with remaining critics")

    remaining_critic: str = Field(
        description="The remaining problem that need to be solved by 'solution'. It must be 'NONE' if satisfied is True")

    solution: str = Field(
        description="The solution that will be applied to fix the remaining problem. Set 'None' if satisfied = 'YES'"
                    "DO NOT use the same value as 'solution' input.")


class CriticSatisfiedSolution(BaseOutput):
    """Always use this schema when user need to verify 'critics and solutions'"""

    satisfied: Literal[True, False] = Field(
        description="Verify whether the solution is applied appropriately, True or False")
    # "If the critic was solved, set value this field True and solution filed 'None'.")

    remaining_critic: str = Field(
        description="The remaining critic/flaw/issuse that need to be solved by 'solution'. It must be 'NONE' if satisfied is True")

    solution: str = Field(
        description="The solution that will be applied to fix the remaining critic. Set 'None' if satisfied = True"
                    "DO NOT use the same value as 'solution' input.")


@register(type='structured_output', name='verification')
class VerificationOutput(BaseOutput):
    """Output schema for the verification agent"""

    css_list: Sequence[CriticSatisfiedSolution] = Field(
        description="The output schema must be either: "
                    "list of dictionary if verify user needs to verify 'critic and solutions' "
                    "OR "
                    "a dictionary if if verify user needs to verify 'prompt'")
