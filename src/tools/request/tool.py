#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import json
import requests
from urllib.parse import urlparse
from typing import Type
from typing_extensions import override
from pydantic import BaseModel, Field

from src.tools.base import BaseTool
from src.registry import RegisterTool
from src.telemetry.telemetry_decorator import telemetry_langchain_tool

HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": "Bearer YOUR_PERSONAL_ACCESS_TOKEN",
    "User-Agent": "MyApp"   # GitHub yêu cầu User-Agent
}


class UrlGetSchema(BaseModel):
    """Input for the tool."""

    url: str = Field(
        default=...,
        description="Url to site need to get content."
    )


@RegisterTool(module=__name__, name="url_get")
class UrlGetTool(BaseTool):
    """Url getting tool."""

    name: str = "url_get"
    description: str = (
        "A tool used to get content on a site provided by an url. "
        "Useful when need to know content/information on a given url. "
        "Also useful when need to know real-time/dynamic information about any particular concept."
        "But just use this when really need, not overuse."
    )
    args_schema: Type[BaseModel] = UrlGetSchema

    @telemetry_langchain_tool("url_get")
    @override
    def _run(self, url: str) -> str:
        """Run tool."""
        url_parser = urlparse(url)

        response = requests.get(url)
        if response.status_code != 200:
            return f"Failed get content on {url!r}. Status code: {response.status_code!r}"
        msg = f"Successfully! Content on '%s': \n\n %s"

        try:
            text = json.dumps(response.text, indent=3)
        except json.JSONDecodeError:
            text = response.text

        return msg % (url, text)
