#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import logging

from pathlib import Path
from typing import Any, Union
from mcp.server import FastMCP
from mcp.types import Icon
from src.utils.file import execute_file, write_script

mcp_server = FastMCP(
    name="Filesystem",
    instructions="The MCP server define tools in filesystem running locally"
)

ICONS = [
    Icon(src='https://cdn-icons-png.flaticon.com/512/2455/2455132.png'),
    Icon(src='https://icons.iconarchive.com/icons/succodesign/love-is-in-the-web/256/heart-icon.png')
]


# Tools
@mcp_server.tool(
    name='execute_python_file',
    title='Python file Executor',
    description='Use to execute a Python file',
    structured_output=True,
    icons=ICONS,
    annotations=None
)
def execute_python_file(file_path: Union[str, Path] = None) -> Any:
    """Execute a Python file

    Args:
        file_path (str): Path to file, relative or absolute

    Returns:
        Dictionary of stdout, stderr, code
    """
    if not file_path:
        raise ValueError(f"Invalid file path '{file_path}'")

    result = execute_file(file_path)
    return result


@mcp_server.tool(
    name='write_to_file',
    title='File Writer',
    description='Use to write content to a file',
    structured_output=True,
    icons=ICONS,
    annotations=None
)
def write_file(content: str, file_path: Union[str, Path]) -> str:
    """Write the content to the file

    Args:
        content (str): Content want to write
        file_path (str): Path to file, relative or absolute

    Returns:
        File path
    """
    write_script(content, file_path)

    return file_path


@mcp_server.tool(
    name='read_from_file',
    title='File Reader',
    description='Use to read content of a file',
    structured_output=True,
    icons=ICONS,
    annotations=None
)
def read_file(file_path: Union[str, Path]) -> str | bytes:
    """Read content in a file

    Args:
        file_path (str): Path to file, relative or absolute

    Returns:
        Content in file
    """
    with open(file_path, 'r') as f:
        return f.read()


@mcp_server.tool(
    name='count_lines',
    title='Line Counter',
    description='Use to count lines of a file',
    structured_output=True,
    icons=ICONS,
    annotations=None
)
def count_lines_in_file(file_path: Union[str, Path]) -> int:
    """Count lines in file

    Args:
        file_path (str): Path to file, relative or absolute

    Returns:
        Number of lines
    """
    with open(file_path, 'r') as f:
        return len(f.readlines())


@mcp_server.tool(
    name='count_words',
    title='Word Counter',
    description='Use to count words of a file',
    structured_output=True,
    icons=ICONS,
    annotations=None
)
def count_words_in_file(file_path: Union[str, Path]) -> int:
    """Count words in file

    Args:
        file_path (str): Path to file, relative or absolute

    Returns:
        Number of words (separated by space)
    """
    with open(file_path, 'r') as f:
        return len(f.read().split(' '))


@mcp_server.tool(
    name='list_dir',
    title='List out the Dir',
    description='Use to list items in a directory',
    structured_output=True,
    icons=ICONS,
    annotations=None
)
def list_dir(dir: Union[str, Path]) -> list[str]:
    """List items in a directory

    Args:
        dir: Path to dir

    Returns:
         List of items in the dir
    """
    import os
    return os.listdir(dir)


# Resources
@mcp_server.resource(
    uri='project://{file}',
    name='read_requirements',
    title="Requirements Read",
    description='Use to read requirements file',
    icons=ICONS,
)
def get_content(file: Union[str, Path]):
    with open(file, 'r') as f:
        content = f.read()

    return f'Content of {file}: \n {content}'


# Prompts
@mcp_server.prompt(
    name='read_file',
    title='Read File',
    description='Instruction to read a file',
    icons=ICONS
)
def read_file(file: Union[str, Path]):
    return [
        {
            "role": "user",
            "content": f"Help me to read the file: {file}"
        }
    ]


def main():
    mcp_server.run(transport='stdio')


if __name__ == '__main__':
    main()
