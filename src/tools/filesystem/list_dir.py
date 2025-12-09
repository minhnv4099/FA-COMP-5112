#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional, Any, Type
from typing_extensions import override

from src.tools.base import BaseTool
from src.tools.mixin import NeedReferenceDirMixin
from src.registry import RegisterTool
from src.telemetry.telemetry_decorator import telemetry_langchain_tool

logger = logging.getLogger(__name__)


class DirListSchema(BaseModel):
    """Input for directory list out tool."""

    dir_path: str = Field(
        ..., description="The path to directory/folder need listing items inside."
    )


@RegisterTool(module=__name__, name="dir_list")
class DirListRun(NeedReferenceDirMixin, BaseTool):
    """Tool that lists out items in a directory/folder"""

    name: str = "dir_list"
    description: str = (
        "A tool that list items inside a directory."
        "Useful when you need to scan items in a the directory."
        "May combine with reading each file."
    )
    args_schema: Type[BaseModel] = DirListSchema

    # test with coroutine
    def _execute(self, dir_path: Path) -> list[str]:
        return os.listdir(dir_path)

    @telemetry_langchain_tool("dir_list")
    @override
    def _run(self, dir_path: str) -> str:
        _dir_path = Path(self.reference_dir) / dir_path

        if not _dir_path.exists():
            logger.error(f"{dir_path!r} is not exist.")
            return f"{dir_path!r} is not exist."

        if _dir_path.is_file():
            logger.error(f"{dir_path!r} is file, cannot list.")
            return f"{dir_path!r} is file, cannot list."
        else:
            items = self._execute(_dir_path)
            logger.info(f"Directory {dir_path!r} has {len(items)} items.")
            return f"Items in {dir_path!r}: {items}"
