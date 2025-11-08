#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar, Union, TYPE_CHECKING, TypeAlias

from omegaconf import ListConfig, DictConfig
from pydantic import BaseModel
from typing_extensions import TypedDict

if TYPE_CHECKING:
    pass

StateLike = Union[TypedDict, BaseModel, dataclass, dict]
"""The generic type for like-state type"""

StateT = TypeVar('StateT', bound=StateLike)
"""The generic type for state (graph state)"""

InputT = TypeVar('InputT', bound=StateLike)
"""The generic type for input state of a graph"""

OutputT = TypeVar('OutputT', bound=StateLike)
"""The generic type for output state of a graph"""

ContextT = TypeVar('ContextT', bound=StateLike)
"""The generic tye of context (runtime) of a graph"""

SchemaLike = Union[BaseModel, StateLike]
"""The generic type for schema"""

SchemaT = TypeVar('SchemaT', bound=SchemaLike)
"""The generic type for schema"""

ToolSchema = TypeVar('ToolSchema', bound=SchemaLike)
"""The argument schema for tool call"""

OutputSchema = TypeVar('OutputSchema', bound=SchemaLike)
"""The schema for structure output"""

ClassLike = TypeVar('ClassLike', bound=object)
""""""

NodeT = TypeVar('NodeT', bound="BaseNode")
""""""

OmegaList: TypeAlias = Union[list, ListConfig]
""""""

OmegaDict: TypeAlias = Union[dict, DictConfig]
""""""

__all__ = [
    'StateLike',
    'StateT',
    'InputT',
    'OutputT',
    'ContextT',
    'SchemaLike',
    'SchemaT',
    'ToolSchema',
    'OutputSchema',
    'ClassLike',
    'NodeT',
    'OmegaDict',
    'OmegaList'
]


def __getattr__(name):
    if name not in __all__:
        raise AttributeError(f"Module {__name__} has no name '{name}'. All available names: {__all__}")
