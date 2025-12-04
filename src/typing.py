#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations

from omegaconf import ListConfig, DictConfig
from dataclasses import dataclass
from pydantic import BaseModel
from typing import TypeVar, Union, TYPE_CHECKING, TypeAlias, Any, Callable, Mapping, Iterable
from typing_extensions import TypedDict

if TYPE_CHECKING:
    from src.node.base import BaseNode

StateLike = Union[TypedDict, dataclass, dict]
"""The generic type for like-state type"""

StateT = TypeVar('StateT', bound=StateLike)
"""The generic type for state (graph state)"""

InputT = TypeVar('InputT', bound=StateLike)
"""The generic type for input state of a graph"""

OutputT = TypeVar('OutputT', bound=StateLike)
"""The generic type for output state of a graph"""

ContextT = TypeVar('ContextT', bound=StateLike)
"""The generic type of context (runtime) of a graph"""

NodeT = TypeVar("NodeT", bound="BaseNode")
"""The generic type of node"""

SchemaLike = Union[BaseModel, dict]
"""The generic type for schema the chat model can bind"""

SchemaT = TypeVar('SchemaT', bound=SchemaLike)
"""The generic type for schema"""

ToolSchema = TypeVar('ToolSchema', bound=SchemaLike)
"""The argument schema for tool call"""

OutputSchema = TypeVar('OutputSchema', bound=SchemaLike)
"""The schema for structure output"""

ClassLike = TypeVar('ClassLike', bound=object)
"""Class like type"""

FunctionLike = TypeVar('FunctionLike', bound=Callable[..., Any])
"""Function like type"""

ListLike: TypeAlias = Union[Iterable, list, ListConfig]
"""List like type"""

MappingLike: TypeAlias = Union[Mapping, dict, DictConfig]
"""Mapping like type"""

__all__ = (
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
    'FunctionLike',
    'ListLike',
    'MappingLike'
)
