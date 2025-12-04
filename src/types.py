#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations

from typing import Any, Optional, Union
from typing_extensions import Annotated, TypedDict, deprecated, NotRequired, Required
from dataclasses import dataclass, field

from src.registry import RegisterState


@deprecated('No need')
class RegisterMetadata(TypedDict):
    """Schema used to register any class"""

    type: str
    """Type of the class such as ``chat``, ``agent``, ...."""
    module: str
    """Module (`.py` file) containing the class"""
    name: str
    """The unique name used to register"""


class RegisterFetchMetadata(TypedDict, total=False):
    """Schema used to fetch a class"""

    type: str
    """Type of the class such as ``chat``, ``agent``, ...."""
    name: str
    """The unique name of registered class"""
    kwargs: NotRequired[dict[str, Any]]
    """Additional keywork arguments"""


@RegisterState(module=__name__, name='base_context')
@dataclass(kw_only=True)
class BaseContext:

    user_id: str = field(
        default='1304391',
    )
