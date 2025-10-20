#
#

#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from dataclasses import dataclass
from typing import Union

from pydantic import BaseModel
from typing_extensions import TypeVar, TypeAlias, TypedDict

StateLike: TypeAlias = Union[BaseModel, dataclass, TypedDict]

StateT = TypeVar("StateT", bound=StateLike)
InputT = TypeVar("InputT", bound=StateLike)
OutputT = TypeVar("OutputT", bound=StateLike)
ContextT = TypeVar("ContextT", bound=StateLike)

NodeT = TypeVar("NodeT", bound=StateLike)
