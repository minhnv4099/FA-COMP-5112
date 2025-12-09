#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import logging
from pathlib import Path
from typing import Optional, Type, Literal
from typing_extensions import override
from pydantic import BaseModel, Field

from langchain_core.callbacks.manager import CallbackManagerForToolRun

from src.tools.base import BaseTool
from src.tools.mixin import NeedReferenceDirMixin
from src.registry import RegisterTool
from src.telemetry.telemetry_decorator import telemetry_langchain_tool

logger = logging.getLogger(__name__)


class FileReadSchema(BaseModel):
    """Input for file reader tool."""

    file_path: str = Field(
        description="The path to file need reading. It can be relative or absolute path."
    )

    encoding: Literal['utf-8', 'latin-1', 'locale'] = Field(
        default='utf-8', description="File encoding (e.g., 'utf-8', 'latin-1')"
    )


@RegisterTool(module=__name__, name="file_read")
class FileReadRun(NeedReferenceDirMixin, BaseTool):
    """Tool that read content of a file."""

    name: str = "file_read"
    description: str = (
        "A tool that read content of a file."
        "Useful when you need to know, evaluate, fix (e.g grammar), improve, reformat the content of the file."
    )
    args_schema: Type[BaseModel] = FileReadSchema

    @telemetry_langchain_tool("file_read")
    @override
    def _run(
        self,
        file_path: str,
        encoding: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Actually run tool."""
        file_to_read = Path(self.reference_dir) / file_path

        try:
            content = file_to_read.read_text(encoding=encoding)
            return f"""Successfully! Content in {file_path!r}:
    ------------------------------ 
    {content}"""
        except FileNotFoundError as e:
            logger.error(f"Error: File not found at {file_to_read!r}")
            return f"Error: File not found at {file_to_read!r}"
        except Exception as e:
            logger.error(f"Error reading file: {str(e)}")
            return f"Error reading file: {str(e)}"
