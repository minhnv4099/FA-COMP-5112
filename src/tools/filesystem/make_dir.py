#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Type, Optional, Union, Any
from typing_extensions import override

from src.tools.base import BaseTool
from src.tools.mixin import NeedReferenceDirMixin, NeedAskHumanMixin
from src.registry import RegisterTool
from src.telemetry.telemetry_decorator import telemetry_langchain_tool

logger = logging.getLogger(__name__)


class DirMakeSchema(NeedAskHumanMixin, BaseModel):
    """Input for directory list out tool."""

    dir_path: str = Field(
        ..., description="The path to directory/folder need making."
    )

    is_temporary: bool = Field(
        default=False, description="The indicator that is just temporary directory."
    )

    ask_human: bool = Field(
        default=True, description="Need to ask human allow you to proceed."
    )


@RegisterTool(module=__name__, name="dir_make")
class DirMakeRun(NeedReferenceDirMixin, BaseTool):
    """Tool that lists out items in a directory/folder"""

    name: str = "dir_make"
    description: str = (
        "A tool that make a directory."
        "Useful when you need to make a directory"
        "That directory can be either temporary or permanent based on context."
        "Always ask human confirm."
    )
    args_schema: Type[BaseModel] = DirMakeSchema

    @telemetry_langchain_tool("dir_make")
    @override
    def _run(
        self,
        dir_path: str,
        ask_human: bool,
        is_temporary: bool = False,
    ) -> str:
        _dir_path = Path(self.reference_dir) / dir_path

        asking_prompt = f"""Confirm making directory at {dir_path!r} (existing?: {_dir_path.exists()}).
Proceed this operation? (y/n): """

        try:
            if ask_human:
                user_confirm = input(asking_prompt).lower().strip()
                if user_confirm == "y":
                    _dir_path.mkdir(parents=True, exist_ok=True)
                else:
                    logger.info("User aborted writing, pass over.")
                    return "User aborted writing, pass over."
            else:
                _dir_path.mkdir(parents=True, exist_ok=True)

            msg = f"Successfully! Created directory at {dir_path!r}."
            if is_temporary:
                msg += '\n'
                msg += 'It is temporary directory, might consider removing it.'

            logger.info(msg)
            return msg
        except Exception as e:
            logger.error(f"Error making directory {dir_path!r}: {e}")
            return f"Error making directory {dir_path!r}: {e}"
