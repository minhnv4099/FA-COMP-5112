#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from typing import Any, Optional
from typing_extensions import override
from langchain_core.runnables import RunnableConfig
from langchain.tools import ToolRuntime

from src.tool.base import BaseDefinedTool
from src.typing import ToolSchema
from src.registry import RegisterTool
from src.tool.schema import UrlReaderArgsSchema


@RegisterTool(module=__name__, name='url_reader')
class UrlReader(BaseDefinedTool):
    """"""

    name: str = "url_reader"  # the 'name' field will be forced to 'name' when register like above.

    description: str = """This tool is called when need to read content in an url"""

    handle_tool_error: str = "Error appears when reading url"

    args_schema: ToolSchema = UrlReaderArgsSchema

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

        import json
        try:
            return json.dumps(response.text, indent=3)
        except json.JSONDecodeError:
            return response.content
