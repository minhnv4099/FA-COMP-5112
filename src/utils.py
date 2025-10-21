#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Union

import yaml
from pydantic import BaseModel
from typing_extensions import TypeVar, TypeAlias, TypedDict

from .base.mapping import get_class

ASSETS_DIR = 'assets/'
""""""
SAVE_CRITIC_DIR = 'assets/rendered_images/critic/'
""""""
SAVE_VERIFICATION_DIR = 'assets/rendered_images/verification/'
"""sss"""

DEFAULT_CAMERA_SETTING_FILE = 'templates/camera_setting'
"""aaa"""
ANCHOR_FILE = 'assets/blender_script/anchor.py'

StateLike: TypeAlias = Union[BaseModel, dataclass, TypedDict]

StateT = TypeVar("StateT", bound=StateLike)
InputT = TypeVar("InputT", bound=StateLike)
OutputT = TypeVar("OutputT", bound=StateLike)
ContextT = TypeVar("ContextT", bound=StateLike)

NodeT = TypeVar("NodeT", bound=StateLike)


def execute(script_path: str):
    python_option = '--python'

    process = subprocess.Popen(
        args=['blender', '--background', python_option, script_path],
        shell=False,
        restore_signals=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    stdout, stderr = process.communicate()
    result = {"error": stderr, 'stdout': stdout, 'returncode': process.returncode}

    process.terminate()
    process.kill()
    process.wait()

    return result


def write_script(script: str, file_path: str) -> None:
    """Write a python script to a file with file path

    Args:
        script (str): Script need to write
        file_path (str|Path): Destination will contain the script

    Returns: None
    """
    with open(file_path, mode='w') as f:
        f.write(script)


def fetch_schema(schema):
    try:
        return get_class(type=schema['type'], name=schema['name'])
    except KeyError:
        return schema


def load_prompt_template_file(prompt: str | Path):
    if prompt is None:
        return dict()
    if os.path.isfile(prompt):
        if prompt.endswith('.yaml'):
            with open(prompt, 'r') as f:
                prompt_dict = yaml.safe_load(f)

            return prompt_dict
        else:
            prompt_content = Path(prompt).read_text()
            return prompt_content
    return prompt


class NotCompletedError(Exception):
    ...


class ScriptWithError(Exception):

    def __init__(self, message: str = None, command=None):
        self.message = message
        self.command = command


class NotFoundEdgeError(ValueError):
    ...
