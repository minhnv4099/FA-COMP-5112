#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from pydantic import BaseModel, Field

from src.registry import RegisterToolSchema


@RegisterToolSchema(module_path=__name__, name='base_tool_schema')
class BaseToolSchema(BaseModel):
    """The Base Tool Schema class"""


class PythonFileExecuteArgsSchema(BaseToolSchema):
    file: str = Field(..., description='the python file')
