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
from src.tool.schema import UrlReaderArgsSchema


@RegisterTool(module_path=__name__, name='url_reader')
class UrlReader(BaseTool):
    """"""

    name: str = 'url_reader'  # the 'name' field will be forced to 'name' when register like above.

    description: str = """This tool is called when need to read content in an url"""

    handle_tool_error: str = "Error appears when reading url"

    args_schema: Type[BaseModel] = UrlReaderArgsSchema

    @override
    def _run(
        self,
        url: str,
        config: Optional[RunnableConfig] = None,
        *,
        runtime: Optional[ToolRuntime] = None
    ) -> Any:

        import requests

        response = requests.get(url)
        if response.status_code != 200:
            return None

        return None
