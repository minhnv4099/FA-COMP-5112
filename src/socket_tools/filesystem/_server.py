#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from src.socket_tools.server import BaseToolServer, CommandType
from typing import final, Any, Callable
from typing_extensions import override
from enum import Enum


def read_file(file_path: str):
    ...


class TypeTool(Callable, Enum):
    READ_FILE = read_file


@final
class FileSystemSocServer(BaseToolServer):

    @override
    def _internal_execute_command(self, command: CommandType | dict) -> dict[str, Any]:
        ...
