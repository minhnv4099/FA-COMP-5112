#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import logging

from pathlib import Path
from typing import Optional, Type
from typing_extensions import override
from pydantic import BaseModel, Field

from langchain_core.callbacks.manager import CallbackManagerForToolRun

from src.tools.base import BaseTool
from src.tools.mixin import NeedReferenceDirMixin, NeedAskHumanMixin
from src.registry import RegisterTool
from src.telemetry.telemetry_decorator import telemetry_langchain_tool

logger = logging.getLogger(__name__)


class FileWriteSchema(BaseModel, NeedAskHumanMixin):
    """Input for file write tool."""

    file_path: str = Field(
        description="The path to file need writing. It can be relative or absolute path."
    )

    content: str = Field(
        description="The content you need to write."
    )

    ask_human: bool = Field(
        default=True, description="Need to ask human allow you to proceed."
    )


@RegisterTool(module=__name__, name="file_write")
class FileWriteRun(NeedReferenceDirMixin, BaseTool):
    """Tool that read content of a file."""

    name: str = "file_write"
    description: str = (
        "A tool that write content to a file, don't use this if the content is empty"
        "Useful when you need to write, save, ... content to the file."
        "Always ask human confirm."
    )
    args_schema: Type[BaseModel] = FileWriteSchema

    @telemetry_langchain_tool("file_write")
    @override
    def _run(
        self,
        file_path: str,
        ask_human: bool,
        content: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        file_to_write = Path(self.reference_dir) / file_path
        display_content = content
        if len(content) > 250:
            display_content = content[:250] + "..."

        asking_prompt = f"""Confirm writing:
    -------------------------------------------
    {display_content}     
    -------------------------------------------
to {file_to_write} (existing?: {file_to_write.exists()})
Proceed this operation? (y/n): """
        try:
            if ask_human:
                user_confirm = input(asking_prompt).lower().strip()
                if user_confirm == "y":
                    file_to_write.write_text(content)
                else:
                    logger.info("User aborted writing, pass over.")
                    return "User aborted writing, pass over."
            else:
                file_to_write.write_text(content)

            # logger.info(f"Successfully! Wrote content: \n\n{display_content}\nto {str(file_path)!r}")
            return f"""Successfully! Wrote content: 
    -------------------------------------------
    {display_content}
    -------------------------------------------
to {str(file_path)!r}."""
        except Exception as e:
            logger.error(f"Error writing to {file_path!r}: {e}")
            return f"Error writing to {file_path!r}: {e}"
