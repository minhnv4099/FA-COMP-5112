#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from pydantic import BaseModel, Field
from typing_extensions import Sequence, Mapping

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
    """Always use this tool to structure your response to user
    when they are asking about retrieve documents from your knowledge and/or external knowledge base."""

    retrieved_docs: list[dict[str, str | list[str]]] = Field(
        description="Only 2 blender document about the given functionality")


@register(type='structured_output', name='coding')
class CodingOutput(BaseOutput):
    """Always use this output schema to response when generating code"""

    script: str = Field(description="Generated script associated with given requirements"
                                    "NOTE: only use 'script' as a key, no any additional prefix or/and suffix character")


@register(type='structured_output', name='critic')
class CriticOutput(BaseOutput):
    """Output schema for the critic agent"""

    critic_fixes: Sequence[Mapping[str, str]] = Field(
        description="Identify critics of rendered images and solutions to fix that")


@register(type='structured_output', name='verification')
class VerificationOutput(BaseOutput):
    """Output schema for the verification agent"""

    verification_solutions: Sequence[Mapping[str, str]] = Field(
        description="Verify if detected critics are solve correctly based suggested fixes, "
                    "and also provide fixes otherwise ")
