#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from abc import ABC

from pydantic import BaseModel, ConfigDict
from langchain_core.tools.base import BaseTool


class BaseToolSchema(BaseModel):
    """The Base Tool Schema class"""


class BaseDefinedTool(BaseTool, ABC):
    """"""

    name: str  # the 'name' field will be forced to 'name' when register like above.

    description: str

    handle_tool_error: str = "Error appears when executing tool"

    args_schema: type[BaseToolSchema]

    model_config = ConfigDict(extra='allow')
