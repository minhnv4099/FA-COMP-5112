#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import os
from typing import Any, Optional, TYPE_CHECKING

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import tool

from src.utils import file

if TYPE_CHECKING:
    ...


@tool(parse_docstring=True)
def execute_script(
    script_path: str,
    run_manager: Optional[CallbackManagerForToolRun] = None,
    **kwargs: Any
) -> Any:
    """The function/tool used to execute script or script file

    Args:
        script_path (str): raw script or file of script
        run_manager (Optional[CallbackManagerForToolRun]):

    Returns: Any
    """
    if not os.path.isfile(script_path):
        script_path = file.write_script(script_path)

    result = file.execute_file(script_path=script_path)

    if len(result['error']) == 0:
        result['error'] = "❇️ ❇️ ❇️ ❇️ ❇️ 👍 👍 👍 👍 👍 NO ERROR 👍 👍 👍 👍 👍 ❇️ ❇️ ❇️ ❇️ ❇️"

    return result['error']


@tool(parse_docstring=True)
def write_script(
    script: str,
    file_path: str = None,
    run_manager: Optional[CallbackManagerForToolRun] = None
) -> None | str:
    """Write a python script to a file with file path

    Args:
        script (str): Script need to write
        file_path (str|Path): Destination will contain the script
        run_manager (CallbackManagerForToolRun, optional):

    Returns: None
    """
    return file.write_script(script, file_path)
