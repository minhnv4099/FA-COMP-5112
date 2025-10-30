#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import os.path
import subprocess
from typing import Any, Optional

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import tool


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
    if not os.path.isfile(script):
        from src.utils import write_script
        script = write_script(script)

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

    if len(result['error']) == 0:
        result['error'] = "❇️ ❇️ ❇️ ❇️ ❇️ 👍 👍 👍 👍 👍 NO ERROR 👍 👍 👍 👍 👍 ❇️ ❇️ ❇️ ❇️ ❇️"

    return result['error']


@tool(parse_docstring=True)
def write_script(script: str, file_path: str = None,
                 run_manager: Optional[CallbackManagerForToolRun] = None) -> None | str:
    """Write a python script to a file with file path

    Args:
        script (str): Script need to write
        file_path (str|Path): Destination will contain the script

    Returns: None
    """
    from src.utils import write_script
    return write_script(script, file_path)
