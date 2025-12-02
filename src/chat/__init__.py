#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations

from typing import TYPE_CHECKING

from src._import_utils import import_attr

if TYPE_CHECKING:
    from src.chat.base import BaseChat
    from src.chat.tool_call_chat import ToolCallGenerateChat, ToolCallExecuteChat
    from src.chat.stateful_chat import (
        StatefulChat,
        ToolCallGenerateStatefulChat,
        ToolCallExecuteStatefulChat
    )

__all__ = (
    "BaseChat",
    "ToolCallGenerateChat",
    "ToolCallExecuteChat",
    "StatefulChat",
    "ToolCallGenerateStatefulChat",
    "ToolCallExecuteStatefulChat"
)

__dynamic_imports = {
    "BaseChat": "base",
    "ToolCallGenerateChat": "tool_call_chat",
    "ToolCallExecuteChat": "tool_call_chat",
    "StatefulChat": "stateful_chat",
    "ToolCallGenerateStatefulChat": "stateful_chat",
    "ToolCallExecuteStatefulChat": "stateful_chat"
}


def __getattr__(attr_name: str):
    module_name = __dynamic_imports.get(attr_name)
    result = import_attr(attr_name, module_name, package=__spec__.parent)
    globals()[attr_name] = result
    return result


def __dir__():
    return list(__all__)
