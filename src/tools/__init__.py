#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import importlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.tools.filesystem import (
        FileReadRun,
        FileWriteRun,
        DirListRun,
        DirMakeRun
     )

    from src.tools.shell.tool import ShellTool
    from src.tools.request.tool import UrlGetTool
    from src.tools.rag.tool import QueryRetrieveTool

__all__ = [
    "FileReadRun",
    "FileWriteRun",
    "DirListRun",
    "DirMakeRun",
    "ShellTool",
    "UrlGetTool",
    "QueryRetrieveTool"
]

_module_lookup = {
    "FileReadRun": "src.tools.filesystem",
    "FileWriteRun": "src.tools.filesystem",
    "DirListRun": "src.tools.filesystem",
    "DirMakeRun": "src.tools.filesystem",
    "ShellTool": "src.tools.shell.tool",
    "UrlGetTool": "src.tools.request.tool",
    "QueryRetrieveTool": "src.tools.rag.tool"
}


def __getattr__(name: str) -> Any:
    if name in _module_lookup:
        module = importlib.import_module(_module_lookup[name])
        return getattr(module, name)
    raise AttributeError(f"Module {__name__!r} has no attribute {name!r}")
