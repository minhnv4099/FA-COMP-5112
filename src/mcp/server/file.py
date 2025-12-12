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
def execute_python_file(ctx: Context, file_path: str) -> dict | str:
    """Execute a Python file.

    Args:
        file_path (str): Path to file, relative or absolute.

    Returns:
        Dictionary of stdout, stderr, status code
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
@telemetry_mcp_tool("write_file")
def write_file(ctx: Context, content: str, file_path: str, kwargs: dict = None) -> str | dict:
    """Write the content to the file

    Args:
        content (str): Content to write
        file_path (str): Path to file, relative or absolute
    """
    file_to_write = Path(file_path)
    try:
        # User confirm
        if not kwargs or "user_confirm" not in kwargs:
            asking_prompt = f"""Confirm writing:
    -------------------------------------------
    {content[:200]}     
    -------------------------------------------
to {str(file_to_write)!r} (existing?: {file_to_write.exists()})
Proceed this operation? (y/n): """

            return {
                "need_user_confirm": True,
                "asking_prompt": asking_prompt
            }

        if kwargs and kwargs["user_confirm"] == 'n':
            logger.info("User aborted executing that tool, pass over, do not need to execute that tool.")
            return "User aborted executing that tool, pass over, do not need to execute that tool."

        file_to_write.write_text(content)

        logger.info(f"Write content to {file_path!r} successfully.")
        return f"Write content to {file_path!r} successfully."
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
        logger.info(f"Read file {file_path!r} successfully.")
        return Path(file_path).read_text()
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
            logger.info(f"Count lines in {file_path!r} successfully.")
            return len(f.readlines())
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
            logger.info(f"Count words in {file_path!r} successfully.")
            return len(f.read().split(' '))
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
        logger.info(f"Items in {dir!r}: {os.listdir(dir)}")
        return f"Items in {dir!r}: {os.listdir(dir)}"
    except Exception as e:
        logger.error(f"Error listing items in {dir!r}: {str(e)}")
        return f"Error listing items in {dir!r}: {str(e)}"


@mcp_server.resource(uri='project://{file}')
@telemetry_resource("project://{file}")
def get_content(ctx: Context, file: str) -> Union[str, bytes]:
    try:
        logger.info(f"Get resource {file!r} successfully.")
        return Path(file).read_text()
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
