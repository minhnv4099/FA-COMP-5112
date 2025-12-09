#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import logging
import platform
import warnings
from contextlib import contextmanager

from typing import Any, Type, Union
from typing_extensions import override
from pydantic import BaseModel, Field, model_validator

from src.tools.base import BaseTool
from src.registry import RegisterTool
from src.telemetry.telemetry_decorator import telemetry_langchain_tool
from src.tools.mixin import NeedAskHumanMixin

logger = logging.getLogger(__name__)

PROHIBITED_CMDS = (
    "touch",
    "rm",
    "rmdir",
)


@contextmanager
def _get_default_bash_process(args: list[str]) -> Any:
    """Get a default bash process."""
    import subprocess

    try:
        with subprocess.Popen(
            args=args,
            shell=False,
            restore_signals=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        ) as process:
            yield process
    finally:
        ...


def _get_platform() -> str:
    """Get platform."""
    system_platform = platform.system()
    if system_platform.lower() == "darwin":
        return "MacOS"
    return system_platform


class ShellInput(BaseModel, NeedAskHumanMixin):
    """commands for the Bash Shell tool."""

    commands: Union[str, list[str]] = Field(
        ...,
        description="List of shell commands to run. Deserialized using json.loads."
    )

    is_safe: bool = Field(
        default=True,
        description="Tell if the command is safe or not."
    )

    ask_human: bool = Field(
        default=True, description="Need to ask human allow you to proceed."
    )

    @model_validator(mode='before')
    @classmethod
    def _validate_commands(cls, values: dict) -> Union[dict, Any]:
        """Validate commands."""
        commands = values.get("commands")
        if commands and isinstance(commands, str):
            values["commands"] = commands.strip().split(" ")

        values["is_safe"] = True
        for cmd in PROHIBITED_CMDS:
            if cmd in values["commands"]:
                values["is_safe"] = False
                warnings.warn(
                    "The shell tool has no safeguards by default."
                )
                break

        return values


@RegisterTool(module=__name__, name='shell_run')
class ShellTool(BaseTool):
    """Tool to run shell commands."""

    name: str = "terminal"
    description: str = (
        f"A tool used to run shell command on this {_get_platform()!r} machine. "
        f"Useful when you need to run bash/shell command including run python file, create, read file, list and other common bash commands. "
        f"Always ask human to confirm execute the command."
    )
    args_schema: Type[BaseModel] = ShellInput

    def _execute_command(self, commands: list[str]):
        try:
            with _get_default_bash_process(commands) as process:

                stdout, stderr = process.communicate()
                result = {
                    "error": stderr,
                    'stdout': stdout,
                    'returncode': process.returncode
                }

                if len(result['error']) == 0:
                    result['error'] = "❇️ ❇️ ❇️ ❇️ ❇️ 👍 👍 👍 👍 👍 NO ERROR 👍 👍 👍 👍 👍 ❇️ ❇️ ❇️ ❇️ ❇️"

                logger.info(f"Execute {commands!r} successfully.")
                return f"Execute {commands!r} successfully. Result: {result}"
        except Exception as e:
            logger.error(f"Error executing {commands!r}: {e}")
            return f"Error executing {commands!r}: {e}"

    @telemetry_langchain_tool("terminal")
    @override
    def _run(
        self,
        commands: Union[str, list[str]],
        is_safe: bool,
        ask_human: bool = True
    ) -> str:
        """Run commands."""
        asking_prompt = f"""Confirm to run commands: 
    -------------------------
    {commands}
    -------------------------
Proceed this? (y/n): """
        if ask_human:
            user_confirm = input(asking_prompt).lower().strip()
            if user_confirm != 'y':
                return "User aborted writing, pass over."
        if is_safe:
            return self._execute_command(commands)
        else:
            return f"Cannot execute {commands} because it is unsafe command!!!"
