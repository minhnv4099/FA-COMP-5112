#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
"""The module containing the base agent class can actually execute tools.
The base agent is non-loop invocation, meaning it takes results from tool execution without check if they are satisfied
```Conversation sample
    > System message
    > Human message (question)
    > AI message (may have tool_call)
    > Tool message or Parse message (parsed structure output from ParseToolCallChat)
```
"""

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
from src.tool.base import BaseDefinedTool
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
        ...

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.tools = self._get_tool_from_schemas()

    @override
    def _internal_tool_call(
        self,
        tool_call: ToolCall,
        **kwargs
    ) -> Union[ToolMessage, ParsedTollCallMessage]:
        # TODO: add docs
        """Actually try to execute tool call first as this class is Agent.
        If no tool (function) is found, treat it as tool schema -> parse output.

        """
        try:
            tool = self.tools[tool_call['name']]
            return tool.invoke(input=tool_call)

        except NotFoundTool as e:
            return super()._internal_tool_call(tool_call)

    def _get_tool_from_schemas(self) -> dict[str, BaseDefinedTool]:
        actual_tools = dict()
        for schema in self.schemas:
            if schema['type'] == 'tool':
                actual_tools[schema['name']] = load_tool(name=schema['name'], **schema['tool_kwargs'])

        return actual_tools
