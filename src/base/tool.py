#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import os
import subprocess
from typing import Any, Optional

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool, tool
from langchain_core.tools.base import ArgsSchema
from pydantic import BaseModel, Field
from typing_extensions import override


class VeryBaseTool(BaseTool):
    name: str
    """Name of tool"""

    description: str
    """Description of the tool, purposes and when it would be called"""

    args_schema: Optional[ArgsSchema]
    """Information about parameter schemas including type, description"""

    return_direct: Optional[bool] = False
    """Whether to return the tool's output directly."""

    def _run(
            self,
            *args: Any,
            run_manager: Optional[CallbackManagerForToolRun] = None,
            **kwargs: Any
    ) -> Any:
        raise NotImplementedError()


class ScriptExecutorArgsSchema(BaseModel):
    script: str = Field(description="Path to file containing script need to execute")
    kwargs: dict = Field(description="Additional keywork arguments", default=None)


class ScriptExecutor(VeryBaseTool):
    """The tool with mission execute Python code, get any yielded error"""

    name: str = "Script Executor"

    description: str = "Given script to run and get error"

    args_schema: Optional[ArgsSchema] = ScriptExecutorArgsSchema

    @override
    def _run(
            self,
            script: str,
            run_manager: Optional[CallbackManagerForToolRun] = None,
            **kwargs: Any
    ) -> Any:
        if "import" in script:
            python_option = "--python-text"
        else:
            assert os.path.isfile(script)
            python_option = '--python'

        cmd = [
            'blender',
            '--background',
            python_option, script,
        ]

        result = subprocess.Popen(
            args=cmd,
            shell=False,
            restore_signals=True,
            text=True,
        )


@tool(parse_docstring=True)
def execute_script(
        script: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs: Any
) -> Any:
    """The function/tool used to execute script or script file

    Args:
        script (str): raw script or file of script
        run_manager (Optional[CallbackManagerForToolRun]):

    Returns: Any
    """
    if "import" in script:
        python_option = "--python-text"
    else:
        assert os.path.isfile(script)
        python_option = '--python'

    process = subprocess.Popen(
        args=['python', script],
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

    return result


@tool(parse_docstring=True)
def write_script(script: str, file_path: str) -> None:
    """Write a python script to a file with file path

    Args:
        script (str): Script need to write
        file_path (str|Path): Destination will contain the script

    Returns: None
    """
    with open(file_path, mode='w') as f:
        f.write(script)
