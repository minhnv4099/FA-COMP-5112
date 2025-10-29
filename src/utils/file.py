#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import os
import subprocess
import base64
import yaml
from pathlib import Path

__all__ = [
    "load_image_content",
    "load_prompt_template_file",
    "execute_file",
    "write_script"
]


def load_image_content(image_path: str):
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode("utf-8")


def execute_file(script_path: str):
    process = subprocess.Popen(
        args=['python', script_path],
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


def write_script(script: str, file_path: str = None) -> None | str:
    """Write a python script to a file with file path

    Args:
        script (str): Script need to write
        file_path (str|Path): Destination will contain the script

    Returns: None
    """
    if file_path is None:
        file_path = 'tmp.py'

    with open(file_path, mode='w') as f:
        f.write(script)

    return file_path


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
