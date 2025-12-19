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

from src.telemetry.telemetry_decorator import telemetry_mcp_tool, telemetry_prompt, telemetry_resource
from src.telemetry.telemetry import record_startup, record_shutdown
from src.mcp.server.utils import require_human_confirm, NeedHumanConfirmException, HumanAbortedException

logger = logging.getLogger("FilesystemMCPServer")

ICONS = [
    Icon(src='https://cdn-icons-png.flaticon.com/512/2455/2455132.png'),
    Icon(src='https://icons.iconarchive.com/icons/succodesign/love-is-in-the-web/256/heart-icon.png')
]


class File(BaseModel):
    file: str
    mode: str


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Life spand for the server"""
    # Setting something here
    try:
        record_startup()
        yield {}
    finally:
        global mcp_server
        logger.info(f"MCP Server {mcp_server.name} shut down.")
        record_shutdown()

mcp_server = FastMCP(
    name="Filesystem",
    instructions="The MCP server define tools in filesystem running locally",
    lifespan=server_lifespan
)


@mcp_server.tool()
@telemetry_mcp_tool("execute_python_file")
def execute_python_file(ctx: Context, file_path: str, aux_kwargs: dict[str, Any] = None) -> dict | str:
    """Execute a Python file.

    Args:
        file_path (str): Path to the file, relative or absolute.

    Returns:
        Dictionary of stdout, stderr, status code
    """
    file_to_write = Path(file_path)

    asking_prompt = f"""
Confirm executing file:
    -------------------------------------------
    {file_path} (existing?: {file_to_write.exists()}).
    -------------------------------------------
Proceed this operation? (y/n): """.lstrip()

    try:
        require_human_confirm(asking_prompt=asking_prompt, kwargs=aux_kwargs)

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

        logger.info(f"Successfully! Executed {file_path!r}. Result: {result}")
        return f"Successfully! Executed {file_path!r}. Result: {result}"
    except NeedHumanConfirmException as e:
        return e.kwargs
    except HumanAbortedException as e:
        return str(e)
    except Exception as e:
        logger.error(f"Error executing {file_path!r}: {str(e)}")
        return f"Error executing {file_path!r}: {str(e)}"


@mcp_server.tool()
@telemetry_mcp_tool("write_file")
def write_file(ctx: Context, content: str, file_path: str, aux_kwargs: dict[str, Any] = None) -> str | dict:
    """Write the content to the file

    Args:
        content (str): Content to write
        file_path (str): Path to file, relative or absolute
    """
    # User confirm
    file_to_write = Path(file_path)

    asking_prompt = f"""
Confirm writing:
    -------------------------------------------
    {content[:200]}     
    -------------------------------------------
to {str(file_to_write)!r} (existing?: {file_to_write.exists()})
Proceed this operation? (y/n): """.lstrip()

    try:
        require_human_confirm(asking_prompt=asking_prompt, kwargs=aux_kwargs)

        file_to_write.write_text(content)

        msg = (
            f"Successfully! Wrote content:"
            f"\n\n"
            f"%s"
            f"\n\n"
            f"to {file_path!r}."
        )
        logger.info(msg % content[:200])
        return msg % content
    except NeedHumanConfirmException as e:
        return e.kwargs
    except HumanAbortedException as e:
        return str(e)
    except Exception as e:
        logger.error(f"Error writing to {file_path!r}: {str(e)}")
        return f"Error writing to {file_path!r}: {str(e)}"


@mcp_server.tool()
@telemetry_mcp_tool("read_file")
async def read_file(ctx: Context, file_path: str) -> str | bytes:
    """Read content in a file

    Args:
        file_path (str): Path to file, relative or absolute

    Returns:
        Content in file
    """
    try:
        content = Path(file_path).read_text()

        logger.info(f"Successfully! Read file {file_path!r}.")
        return f"Successfully! Content in {file_path!r}:\n{'-'*50}\n{content}"
    except Exception as e:
        logger.error(f"Error reading {file_path!r}: {str(e)}")
        return f"Error reading {file_path!r}: {str(e)}"


@mcp_server.tool()
@telemetry_mcp_tool("count_lines_in_file")
def count_lines_in_file(ctx: Context, file_path: str) -> int | str:
    """Count lines in file

    Args:
        file_path (str): Path to file, relative or absolute

    Returns:
        Number of lines
    """
    try:
        with open(file_path, 'r') as f:
            n_lines = len(f.readlines())

        logger.info(f"Successfully! Count lines in {file_path!r}: {n_lines}")
        return n_lines
    except Exception as e:
        logger.info(f"Error counting lines in {file_path!r}. {str(e)}")
        return f"Error counting lines in {file_path!r}. {str(e)}"


@mcp_server.tool()
@telemetry_mcp_tool("count_words_in_file")
def count_words_in_file(ctx: Context, file_path: str) -> int | str:
    """Count words in file

    Args:
        file_path (str): Path to file, relative or absolute

    Returns:
        Number of words (separated by space)
    """
    try:
        with open(file_path, 'r') as f:
            n_words = len(f.read().split(' '))

        logger.info(f"Successfully! Count words in {file_path!r}.")
        return n_words
    except Exception as e:
        logger.error(f"Error counting words in {file_path!r}. {str(e)}")
        return f"Error counting words in {file_path!r}. {str(e)}"


@mcp_server.tool()
@telemetry_mcp_tool("list_dir")
def list_dir(ctx: Context, dir: str) -> str:
    """List items in a directory

    Args:
        dir: Path to dir

    Returns:
         List of items in the dir
    """
    try:
        items = os.listdir(dir)

        logger.info(f"{dir!r} has {len(items)} items.")
        return f"Successfully! Items in {dir!r}: {items}"
    except Exception as e:
        logger.error(f"Error listing items in {dir!r}: {str(e)}")
        return f"Error listing items in {dir!r}: {str(e)}"


@mcp_server.resource(uri='project://{file}')
@telemetry_resource("project://{file}")
def get_content(ctx: Context, file: str) -> Union[str, bytes]:
    try:
        content = Path(file).read_text()

        logger.info(f"Successfully! Got resource {file!r}.")
        return content
    except Exception as e:
        logger.error(f"Error reading {file!r}: {str(e)}")
        return f"Error reading {file!r}: {str(e)}"


@mcp_server.prompt()
@telemetry_prompt(f"{mcp_server.name}--general_system_prompt")
def general_system_prompt(ctx: Context):
    return """You are a very helpful assistance."""


def main():
    transport: Literal["stdio", "sse", "streamable-http"] = "stdio"
    logger.info(f'MCP Server Filesystem is running on transport {transport!r}')
    mcp_server.run(transport=transport)


if __name__ == '__main__':
    main()
