#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from typing import Any, Type, Optional
from typing_extensions import override
from langchain_core.runnables import RunnableConfig
from langchain.tools import ToolRuntime
from pydantic import BaseModel

from langchain_core.tools import BaseTool

from src.registry import RegisterTool
from src.tool.schema import (
    PythonFileExecuteArgsSchema,
    PythonFileWriteArgsSchema,
    BashCommand
)


@RegisterTool(module_path=__name__, name='execute_python')
class PythonFileExecutor(BaseTool):
    """"""

    name: str = 'execute_python'  # the 'name' field will be forced to 'name' when register like above.

    description: str = """This tool is called when need to execute python file"""

    handle_tool_error: str = "Error appears when executing Python file"

    args_schema: Type[BaseModel] = PythonFileExecuteArgsSchema

    @override
    def _run(
        self,
        file: str,
        config: Optional[RunnableConfig] = None,
        *,
        runtime: Optional[ToolRuntime] = None
    ) -> Any:
        import subprocess

        process = subprocess.Popen(
            args=['python', file],
            shell=False,
            restore_signals=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        stdout, stderr = process.communicate()
        result = {"error": stderr, 'stdout': stdout, 'returncode': process.returncode}

        process.terminate()
        process.kill()
        process.wait()

        if len(result['error']) == 0:
            result['error'] = "❇️ ❇️ ❇️ ❇️ ❇️ 👍 👍 👍 👍 👍 NO ERROR 👍 👍 👍 👍 👍 ❇️ ❇️ ❇️ ❇️ ❇️"

        return result


@RegisterTool(module_path=__name__, name='write_script')
class PythonFileWriter(BaseTool):
    """"""

    name: str = 'write_script'  # the 'name' field will be forced to 'name' when register like above.

    description: str = """This tool is called when need to write Python script to a file"""

    handle_tool_error: str = "Error appears when write script to Python file"

    args_schema: Type[BaseModel] = PythonFileWriteArgsSchema

    @override
    def _run(self, script: str, file: str) -> Any:
        with open(file, 'w') as f:
            f.write(script)

        return f"Wrote script to file '{file}'"


@RegisterTool(module_path=__name__, name='bash_execute')
class BashExecutor(BaseTool):
    """"""

    name: str = 'bash_execute'  # the 'name' field will be forced to 'name' when register like above.

    description: str = """This tool is called when need to execute a bash command"""

    handle_tool_error: str = "Error appears when executing a bash command"

    args_schema: Type[BaseModel] = BashCommand

    @override
    def _run(self, command: list[str]) -> Any:
        import subprocess
        result = subprocess.run(command)

        return result.__str__()
