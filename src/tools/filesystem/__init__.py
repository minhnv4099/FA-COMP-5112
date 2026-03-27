#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from src.tools.filesystem.read import FileReadRun
from src.tools.filesystem.write import FileWriteRun
from src.tools.filesystem.list_dir import DirListRun
from src.tools.filesystem.make_dir import DirMakeRun


__all__ = [
    "FileReadRun",
    "FileWriteRun",
    "DirListRun",
    "DirMakeRun"
]


from pathlib import Path
from typing import Optional
from langchain_core.tools import tool


BASE_DIR = Path.cwd()


def _resolve_path(file_path: str) -> Path:
    """Ensure all paths stay within BASE_DIR."""
    path = (BASE_DIR / file_path).resolve()
    if not str(path).startswith(str(BASE_DIR)):
        raise ValueError("Access outside base directory is not allowed.")
    return path


@tool
def read_file(file_path: str) -> str:
    """Read the contents of a file."""
    path = _resolve_path(file_path)
    if not path.exists():
        return f"File not found: {file_path}"
    if not path.is_file():
        return f"{file_path!r} is a folder"
    return path.read_text(encoding="utf-8")


@tool
def write_file(file_path: str, content: str) -> str:
    """Write content to a file (overwrite if exists)."""
    path = _resolve_path(file_path)
    if not path.exists():
        return f"File not found: {file_path}"
    if not path.is_file():
        return f"{file_path!r} is a folder"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"File written: {file_path}"


@tool
def append_file(file_path: str, content: str) -> str:
    """Append content to a file."""
    path = _resolve_path(file_path)
    if not path.exists():
        return f"File not found: {file_path}"
    if not path.is_file():
        return f"{file_path!r} is a folder"

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(content)
    return f"Content appended to: {file_path}"


@tool
def list_files(directory: str) -> str:
    """List files in a directory."""
    path = _resolve_path(directory)
    if not path.is_dir():
        return f"Directory not found: {directory}"
    files = [str(p.name) for p in path.iterdir()]
    return "\n".join(files)


@tool
def delete_file(file_path: str) -> str:
    """Delete a file."""
    path = _resolve_path(file_path)
    if not path.exists():
        return f"File not found: {file_path}"
    if not path.is_file():
        return f"{file_path!r} is a folder"

    path.unlink()
    return f"Deleted: {file_path}"
