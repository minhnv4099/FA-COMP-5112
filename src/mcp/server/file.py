#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import os
import logging

import subprocess
from typing import Union, Literal, AsyncIterator, Dict, Any
from pathlib import Path
from mcp.server.fastmcp.server import Context
from mcp.types import Icon
from contextlib import asynccontextmanager
from src.mcp.server.utils import require_human_confirm, NeedHumanConfirmException, HumanAbortedException
from src.mcp.server.wrapper import AccessibleFastMCP


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s #%(lineno)d'
)
logger = logging.getLogger("FilesystemMCPServer")

ICONS = [
    Icon(src='https://cdn-icons-png.flaticon.com/512/2455/2455132.png'),
    Icon(src='https://icons.iconarchive.com/icons/succodesign/love-is-in-the-web/256/heart-icon.png')
]


@asynccontextmanager
async def server_lifespan(server: AccessibleFastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Lifespan for the server"""
    # Setting something here
    try:
        logger.info(f'Accessible directories: {[str(s) for s in SANDBOX_DIRS]}.')
        logger.info(f"A new session connected to MCP Server {server.name!r}.")
        yield {}
    finally:
        logger.info(f"A session disconnected MCP Server {server.name!r}")

mcp_server = AccessibleFastMCP(
    name="Filesystem",
    instructions="The MCP server define tools related to filesystem running locally",
    lifespan=server_lifespan,
    port=10000
)

PWD = Path.cwd()

# tempopary solution
SANDBOX_DIRS = [
    PWD / '.workspace',
]


def _resolve_path(file_path: str) -> Path:
    """Ensure all paths stay within BASE_DIR."""
    for sand_dir in SANDBOX_DIRS:
        path = (sand_dir / file_path).resolve()
        if str(path).startswith(str(sand_dir)):
            return path

    logger.critical('Attempted to access non-allowed directories!!!')
    raise ValueError(f"Access outside {SANDBOX_DIRS!r} is not allowed.")


@mcp_server.tool()
async def get_accessible_dir():
    """Get information about directories you are allowed to access.
    Accessing others dir is not allowed and causes error.
    """
    for s in SANDBOX_DIRS:
        if not s.exists():
            s.mkdir(exist_ok=True, parents=True)

    return [str(s) for s in SANDBOX_DIRS]


@mcp_server.tool(human_confirm=True)
async def execute_python_file(ctx: Context, file_path: str, aux_kwargs: dict[str, Any] = None) -> dict | str:
    """Execute a Python file.

    Args:
        file_path (str): Path to the file, relative or absolute.

    Returns:
        Dictionary of stdout, stderr, status code
    """
    file_to_execute = _resolve_path(file_path)
    if not file_to_execute.exists():
        return f"File {file_path!r} not found"

    if not file_to_execute.is_file() and file_to_execute.is_dir():
        return f"{file_path!r} is a folder"

    asking_prompt = f"""
Confirm executing file:
    -------------------------------------------
    {file_path} (existing?: {file_to_execute.exists()}).
    -------------------------------------------
Proceed this operation? (y/n): """.lstrip()

    try:
        # require_human_confirm(asking_prompt=asking_prompt, kwargs=aux_kwargs)

        with subprocess.Popen(
            args=['python', file_to_execute],
            shell=False,
            restore_signals=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        ) as process:
            stdout, stderr = process.communicate()
            result = {"error": stderr, 'stdout': stdout, 'returncode': process.returncode}

        logger.info(f"Executed {file_path!r}.")
        return f"Executed {file_path!r}. Acquired result: {result}"
    except NeedHumanConfirmException as e:
        return e.kwargs
    except HumanAbortedException as e:
        return str(e)
    except Exception as e:
        logger.error(f"Error executing {file_path!r}: {str(e)}")
        return f"Error executing {file_path!r}: {str(e)}"


@mcp_server.tool(human_confirm=True)
async def write_file(ctx: Context, content: str, file_path: str, aux_kwargs: dict[str, Any] = None) -> str | dict:
    """Write the content to the file

    Args:
        content (str): Content to write
        file_path (str): Path to file, relative or absolute
    """
    file_to_write = Path(file_path)

    # User confirm
    asking_prompt = f"""
Confirm writing:
    -------------------------------------------
    {content[:200]}     
    -------------------------------------------
to {str(file_to_write)!r} (existing?: {file_to_write.exists()})
Proceed this operation? (y/n): """.lstrip()

    try:
        # require_human_confirm(asking_prompt=asking_prompt, kwargs=aux_kwargs)
        file_to_write.write_text(content)

        msg = (
            f"Wrote content:"
            f"\n\n"
            f"%s"
            f"\n\n"
            f"to {file_path!r}."
        )
        # logger.info(msg % content[:200])
        return msg % content
    except NeedHumanConfirmException as e:
        return e.kwargs
    except HumanAbortedException as e:
        return str(e)
    except Exception as e:
        logger.error(f"Error writing to {file_path!r}: {str(e)}")
        return f"Error writing to {file_path!r}: {str(e)}"


@mcp_server.tool(human_confirm=['approve', 'reject'])
async def read_file(ctx: Context, file_path: str) -> str | bytes:
    """Read content in a file

    Args:
        file_path (str): Path to file, relative or absolute

    Returns:
        Content in file
    """
    path = _resolve_path(file_path)
    if not path.exists():
        return f"File {file_path!r} not found"

    if not path.is_file() and path.is_dir():
        return f"{file_path!r} is a folder"

    try:
        content = path.read_text(encoding="utf-8")
        return f"Content in {file_path!r}:\n\n{'-'*50}\n{content}"
    except Exception as e:
        return f"Error reading {file_path!r}: {str(e)}"


@mcp_server.tool()
async def count_lines_in_file(ctx: Context, file_path: str) -> int | str:
    """Count lines in file

    Args:
        file_path (str): Path to file, relative or absolute

    Returns:
        Number of lines
    """
    path = _resolve_path(file_path)
    if not path.exists():
        return f"File {file_path!r} not found"

    if not path.is_file() and path.is_dir():
        return f"{file_path!r} is a folder"

    try:
        with open(path, 'r') as f:
            n_lines = len(f.readlines())

        return f"Line count in {file_path!r} is {n_lines}."
    except Exception as e:
        return f"Error counting lines in {file_path!r}. {str(e)}"


@mcp_server.tool()
async def count_words_in_file(ctx: Context, file_path: str) -> int | str:
    """Count words in file

    Args:
        file_path (str): Path to file, relative or absolute

    Returns:
        Number of words (separated by space)
    """
    path = _resolve_path(file_path)
    if not path.exists():
        return f"File {file_path!r} not found"

    if not path.is_file() and path.is_dir():
        return f"{file_path!r} is a folder"

    try:
        with open(path, 'r') as f:
            n_words = len(f.read().split(' '))

        return f"Word count in {file_path!r} is {n_words}."
    except Exception as e:
        return f"Error counting words in {file_path!r}. {str(e)}"


@mcp_server.tool()
async def list_dir(ctx: Context, dir: str) -> str:
    """List items in a directory

    Args:
        dir: Path to dir

    Returns:
         List of items in the dir
    """
    path = _resolve_path(dir)
    if not path.exists():
        return f"Folder {dir!r} not found"

    if path.is_file() and not path.is_dir():
        return f"{dir!r} is a file"
    try:
        items = os.listdir(path)

        return f"Items in {dir!r}:\n\n {items}"
    except Exception as e:
        return f"Error listing items in {dir!r}: {str(e)}"


@mcp_server.resource(uri='project://{file}')
async def get_content(ctx: Context, file: str) -> Union[str, bytes]:
    path = _resolve_path(file)
    if not path.exists():
        return f"File {file!r} not found"
    if not path.is_file():
        return f"{file!r} is a folder"

    try:
        content = path.read_text(encoding='utf-8')
        return content
    except Exception as e:
        return f"Error reading {file!r}: {str(e)}"


@mcp_server.prompt()
async def general_system_prompt(ctx: Context):
    return """You are a very helpful assistance."""


def main():
    from src.mcp.manager import run_mcp_server
    with run_mcp_server(mcp_server):
        mcp_server.run(transport="sse")


if __name__ == '__main__':
    main()
