#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import os
from typing import Any, Optional, TYPE_CHECKING
from typing_extensions import override

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import tool

from src.registry import RegisterTool
from src.tool.rag import QueryRetriever
from src.tool.schema import QueryRetrieveArgsSchema
from src.utils import file

if TYPE_CHECKING:
    from src.typing import ToolSchema


class BlenderRetrieverArgsSchema(QueryRetrieveArgsSchema):
    """Use this schema when need writing or saving Python script/code to a file"""


@RegisterTool(module=__name__, name="blender_query_retriever")
class BlenderQueryRetriever(QueryRetriever):

    name: str = 'blender_query_retriever'

    description: str = """Always use this tool to retrieve documents, supporting the query."""

    args_schema: ToolSchema = QueryRetrieveArgsSchema

    @override
    def _run(self, query: str, *args: Any, **kwargs: Any) -> Any:
        docs = self.retrieving_engine.invoke(query)
        contents = [doc.page_content for doc in docs]

        return f"\n\n{'='*100}\n".join(contents)


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
