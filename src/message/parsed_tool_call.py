#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import logging
from typing import Any

from langchain_core.messages import ChatMessage, ToolMessage, BaseMessage

logger = logging.getLogger(__name__)


class ParsedTollCallMessage(ToolMessage):
    """The Parsed Tool Call representing structured output parsed from a tool call distinguishing with Tool Message
    """

    type: str = "Parser"

    role: str = 'assistance'

    def __init__(
        self,
        content: str,
        tool_call_id: str,
        name: str = None,
        raw_content: dict = None,
        *args, **kwargs
    ):
        super().__init__(
            content=content,
            tool_call_id=tool_call_id,
            *args,
            **kwargs
        )
        self.name = name if name else self.tool_call_id
        self.raw_content = raw_content if raw_content else dict()

    def get_field(self, field: str = None, default=None) -> Any:
        if field not in self.raw_content:
            logger.critical(f"'{field}' not in available fields: {list(self.raw_content.keys())}")
            keys = list(self.raw_content.keys())
            if len(keys) == 1:
                logger.info(f"As the message has only 1 field ('{keys[0]}', get it by default)")
                return self.raw_content.get(keys[0], default)
            else:
                return KeyError(f"Now we just support to get ONE field, but there are {len(keys)} fields: {keys}, "
                                f"we don't know which field you want to get.")

        return self.raw_content.get(field, default)
