#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
"""The module containing agent classes, with command and different capabilities"""
from __future__ import annotations

import logging
from typing import Union, Generic
from typing_extensions import override

from langchain_core.messages import ToolMessage
from langchain_core.tools.base import ToolCall

from src.registry import RegisterAgent, load_tool
from src.types import StateT, OutputT, ToolSchema, ContextT
from src.chat.parsable_chat import ParseToolCallChat
from src.message.parsed_tool_call import ParsedTollCallMessage
from src.utils.exception import NotFoundTool

logger = logging.getLogger(__name__)


@RegisterAgent(module_path=__name__, name='base_agent')
class BaseAgent(
    ParseToolCallChat,
    Generic[StateT, ContextT, OutputT, ToolSchema],
):
    # TODO: add docs
    """The Base Agent class using single system prompt and human template and being able to execute tools.\n
    However, just execute tools one once (no persistence)"""
    def __init_subclass__(cls):
        # super().__init_subclass__()
        ...

    @override
    def _internal_tool_call(
        self,
        tool_call: ToolCall,
        **kwargs
    ) -> Union[ToolMessage, ParsedTollCallMessage]:
        # TODO: add docs
        """Actually try to execute tool call first as this class is Agent.
        If no tool (function) found, treat it as tool schema.

        """
        try:
            tool = load_tool(name=tool_call['name'], **kwargs)
            return tool.invoke(input=tool_call)

        except NotFoundTool as e:
            return super()._internal_tool_call(tool_call)
