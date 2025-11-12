#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
"""The module containing agent classes, with command and different capabilities"""
from __future__ import annotations

import logging
from typing import Union, Generic

from langchain_core.messages import ToolMessage
from langchain_core.tools.base import ToolCall

from src.registry import RegisterAgent, load_tool
from src.types import OutputT, ToolSchema
from src.chat.tool_call_chat import ToolCallChat
from src.utils.exception import NotFoundTool

logger = logging.getLogger(__name__)


@RegisterAgent(module_path=__name__, name='tool_call_agent')
class BaseAgent(ToolCallChat, Generic[OutputT, ToolSchema]):
    """The Base Agent class using single system prompt and human template and being able to execute tools.\n
    However, just execute tools one once (no persistence)"""
    def __init_subclass__(cls):
        # super().__init_subclass__()
        ...

    def _internal_tool_call(self, tool_call: ToolCall) -> ToolMessage:
        """Actually try to execute tool call first as this class is Agent. If no tool (function) found, treat it as tool schema."""

        try:
            return self._execute_tool(tool_call)

        except NotFoundTool as e:
            return super()._internal_tool_call(tool_call)

    def _execute_tool(self, tool_call: Union[ToolCall]):
        tool = load_tool(tool_call['name'])

        return tool.invoke(input=tool_call)
