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
    > Tool message or Parse message (parsed structure output from ToolCallGenerateChat)
```
"""

from __future__ import annotations

import logging
from typing import Generic

from src.registry import RegisterAgent
from src.typing import StateT, OutputT, ToolSchema, ContextT
from src.chat.tool_call_chat import ToolCallExecuteChat

logger = logging.getLogger(__name__)


@RegisterAgent(module=__name__, name='base_agent')
class BaseAgent(
    ToolCallExecuteChat,
    Generic[StateT, ContextT, OutputT, ToolSchema],
):
    """"""
