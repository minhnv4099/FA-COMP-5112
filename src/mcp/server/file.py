#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import os
import logging

import subprocess
from typing import Union, Literal, AsyncIterator, Dict, Any
from pathlib import Path
from pydantic import BaseModel
from mcp.server import FastMCP
from mcp.server.fastmcp.server import Context
from mcp.types import Icon
from contextlib import asynccontextmanager

logger = logging.getLogger("FilesystemMCPServer")

ICONS = [
    Icon(src='https://cdn-icons-png.flaticon.com/512/2455/2455132.png'),
    Icon(src='https://icons.iconarchive.com/icons/succodesign/love-is-in-the-web/256/heart-icon.png')
]


class File(BaseModel):
    file: str | Path
    mode: str


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Life spand for the server"""
    # Setting something here
    try:
        yield {}
    finally:
        global mcp_server
        logger.info(f"MCP Server {mcp_server.name} shut down.")


mcp_server = FastMCP(
    name="Filesystem",
    instructions="The MCP server define tools in filesystem running locally",
    lifespan=server_lifespan
)

@mcp_server.tool()
def execute_python_file(ctx: Context, file_path: str) -> dict | str:
    """Execute a Python file.

    Args:
        file_path (str): Path to file, relative or absolute.

    Returns:
        Dictionary of stdout, stderr, code
    """
    try:
        with subprocess.Popen(
            args=['python', file_path],
            shell=False,
            restore_signals=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        ) as process:
            stdout, stderr = process.communicate()
            result = {"error": stderr, 'stdout': stdout, 'returncode': process.returncode}

            process.terminate()
            process.kill()

            logger.info(f"Execute {file_path!r} successfully. {result}")
            return result
    except Exception as e:
        logger.error(f"Error {file_path!r} is not exist.")
        return f"Error executing {file_path!r}: {str(e)}"


@mcp_server.tool()
def write_file(ctx: Context, content: str, file_path: str) -> str:
    """Write the content to the file

    Args:
        content (str): Content to write
        file_path (str): Path to file, relative or absolute
    """
    try:
        Path(file_path).write_text(content)
        logger.info(f"Write content to {file_path!r} successfully.")
        return f"Write content to {file_path!r} successfully."
    except Exception as e:
        logger.error(f"Error writing to {file_path!r}: {str(e)}")
        return f"Error writing to {file_path!r}: {str(e)}"


@mcp_server.tool()
async def read_file(ctx: Context, file_path: File) -> str | bytes:
    """Read content in a file

    Args:
        file_path (str): Path to file, relative or absolute

    Returns:
        Content in file
    """
    try:
        logger.info(f"Read file {file_path!r} successfully.")
        return Path(file_path.file).read_text()
    except Exception as e:
        logger.error(f"Error reading {file_path!r}: {str(e)}")
        return f"Error reading {file_path!r}: {str(e)}"


@mcp_server.tool()
def count_lines_in_file(ctx: Context, file_path: str) -> int | str:
    """Count lines in file

    Args:
        file_path (str): Path to file, relative or absolute

    Returns:
        Number of lines
    """
    try:
        with open(file_path, 'r') as f:
            logger.info(f"Count lines in {file_path!r} successfully.")
            return len(f.readlines())
    except Exception as e:
        logger.info(f"Error counting lines in {file_path!r}. {str(e)}")
        return f"Error counting lines in {file_path!r}. {str(e)}"


@mcp_server.tool()
def count_words_in_file(ctx: Context, file_path: str) -> int | str:
    """Count words in file

    Args:
        file_path (str): Path to file, relative or absolute

    Returns:
        Number of words (separated by space)
    """
    try:
        with open(file_path, 'r') as f:
            logger.info(f"Count words in {file_path!r} successfully.")
            return len(f.read().split(' '))
    except Exception as e:
        logger.error(f"Error counting words in {file_path!r}. {str(e)}")
        return f"Error counting words in {file_path!r}. {str(e)}"


@mcp_server.tool()
def list_dir(ctx: Context, dir: str) -> str:
    """List items in a directory

    Args:
        dir: Path to dir

    Returns:
         List of items in the dir
    """
    try:
        logger.info(f"Items in {dir!r}: {os.listdir(dir)}")
        return f"Items in {dir!r}: {os.listdir(dir)}"
    except Exception as e:
        logger.error(f"Error listing items in {dir!r}: {str(e)}")
        return f"Error listing items in {dir!r}: {str(e)}"


@mcp_server.resource(uri='project://{file}')
def get_content(ctx: Context, file: str) -> Union[str, bytes]:
    try:
        logger.info(f"Get resource {file!r} successfully.")
        return Path(file).read_text()
    except Exception as e:
        logger.error(f"Error reading {file!r}: {str(e)}")
        return f"Error reading {file!r}: {str(e)}"


@mcp_server.prompt()
def general_system_prompt(ctx: Context):
    return [
        {
            "role": "user",
            "content": f"You are a very helpful assistance."
        }
    ]


def main():
    transport: Literal["stdio", "sse", "streamable-http"] = "stdio"
    logger.info(f'MCP Server Filesystem is running on transport {transport!r}')
    mcp_server.run(transport=transport)


if __name__ == '__main__':
    main()
