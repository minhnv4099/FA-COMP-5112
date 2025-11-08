#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from typing import Any, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel

from src.registry import RegisterTool
from src.tool.schema import PythonFileExecuteArgsSchema


@RegisterTool(module_path=__name__, name='execute_python')
class PythonFileExecutor(BaseTool):
    """"""

    name: str = 'execute_python'

    description: str = 'Execute python file'

    args_schema: Type[BaseModel] = PythonFileExecuteArgsSchema

    def _run(self, file: str) -> Any:
        if 'code' in file:
            return f"Failed to execute '{file}'"

        return f"File '{file}' is executed successfully."
