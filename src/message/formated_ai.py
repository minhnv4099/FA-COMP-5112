#
#  Copyright (c) 2026
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations
from typing import Optional, Any, Union
from langchain_core.messages import AIMessage


class FormattedAIMessage(AIMessage):
    """AI Message class with some features to get formated fields."""

    @property
    def reasoning_content(self):
        return self.additional_kwargs['reasoning_content']

