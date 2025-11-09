#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from typing import Literal
from typing_extensions import Sequence
from pydantic import BaseModel, Field

from src.registry import RegisterChatOutputSchema
from src.utils.decorator import add_note_docstring

__all__ = [
    "BaseOutput",
    "PlannerOutput",
    "RetrieverOutput",
    "CodingOutput",
    "CriticOutput",
    "VerificationOutput",
]

module_path = __name__


class BaseOutput(BaseModel):
    """Always use this schema and its subclasses to format the answers
    This class is an abstractive class for all structured outputs in the graph"""

    # content: str = Field(..., description='Content of ai response, ignore this field if there any other fields')


@add_note_docstring(docs="Used for only 'COMP-5112' project")
@RegisterChatOutputSchema(name='planner', module_path=module_path)
class PlannerOutput(BaseOutput):
    """Always use this schema whenever returning final response
    Given a task such create a 3d chair, break it into smaller ones [create legs, backseat, backrest, ...]"""

    subtasks: Sequence[str] = Field(description="List of smaller subtasks after breaking a big task with any additional"
                                                "supplementary")


@add_note_docstring(docs="Used for only 'COMP-5112' project")
@RegisterChatOutputSchema(name='retriever', module_path=module_path)
class RetrieverOutput(BaseOutput):
    """Always use this tool to structure your response"""

    summary: str = Field(
        description="Summary of query and retrieved documents.")


@add_note_docstring(docs="Used for only 'COMP-5112' project")
@RegisterChatOutputSchema(name='coding', module_path=module_path)
class CodingOutput(BaseOutput):
    """Always use this output schema to response when generating code"""

    script: str = Field(
        description="Generated script. NOTE: only use 'script' as a key, no any additional prefix or/and suffix character")


@add_note_docstring(docs="Used for only 'COMP-5112' project")
class CriticSolutionPair(BaseOutput):
    """The output schema for a single pair of critic and fix"""

    critic: str = Field(description="A critic that exists in an image")

    solution: str = Field(description="A solution (action, adjustment) that used by coding agent to "
                                      "modify the script and fix the critic")


@add_note_docstring(docs="Used for only 'COMP-5112' project")
@RegisterChatOutputSchema(name='critic', module_path=module_path)
class CriticOutput(BaseOutput):
    """Output schema for the critic agent"""

    critic_solution_list: Sequence[CriticSolutionPair] = Field(
        description="List of (critic, solution) pairs in the given image")


@add_note_docstring(docs="Used for only 'COMP-5112' project")
class SatisfiedSolution(BaseOutput):
    """Always use this schema when need to verify 'critics and solutions'"""

    satisfied: Literal[True, False] = Field(
        description="Verify whether the solution is applied appropriately, True or False")

    new_critic: str = Field(
        description="The new critic/flaw/issuse that need to be solved by 'solution'. It must be 'NONE' if satisfied is True")

    solution: str = Field(
        description="The solution that will be applied to fix the remaining critic. Set 'None' if satisfied = True"
                    "DO NOT use the same value as 'solution' input.")


@add_note_docstring(docs="Used for only 'COMP-5112' project")
@RegisterChatOutputSchema(name='verification', module_path=module_path)
class VerificationOutput(BaseOutput):
    """Output schema for the verification agent"""

    ss_list: Sequence[SatisfiedSolution] = Field(
        description="The output schema must be either: "
                    "list of dictionary if verify user needs to verify 'critic and solutions' "
                    "OR "
                    "a dictionary if if verify user needs to verify 'prompt'")
