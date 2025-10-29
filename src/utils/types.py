#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from typing import TypeVar, TypeAlias, Union
from typing_extensions import TypedDict
from pydantic import BaseModel
from dataclasses import dataclass

__all__ = [
    "BaseModel",
    "dataclass",
    "TypedDict",
    "TypeVar",
    "TypeAlias",
    "Union",
    "StateLike",
    "StateT",
    "InputT",
    "OutputT",
    "ContextT",
    "NodeT"
]

StateLike: TypeAlias = Union[BaseModel, dataclass, TypedDict]

StateT = TypeVar("StateT", bound=StateLike)
InputT = TypeVar("InputT", bound=StateLike)
OutputT = TypeVar("OutputT", bound=StateLike)
ContextT = TypeVar("ContextT", bound=StateLike)

NodeT = TypeVar("NodeT", bound=StateLike)
