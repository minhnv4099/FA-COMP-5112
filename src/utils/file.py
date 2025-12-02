#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import os
import subprocess
import base64
from typing import Union

import yaml
import html
import ast
import re
from pathlib import Path

__all__ = [
    "load_image_content",
    "load_prompt_template_file",
    "execute_file",
    "write_script",
    "clean_text"
]


def load_image_content(image_path: str):
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode("utf-8")


def execute_file(script_path: str):
    output = subprocess.Popen(
        args=['python', script_path],
        shell=False,
        restore_signals=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    stdout, stderr = output.communicate()
    result = {"error": stderr, 'stdout': stdout, 'returncode': output.returncode}

    output.terminate()
    output.kill()
    output.wait()

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

    with open(file_path, mode='w', encoding='utf-8') as f:
        f.write(clean_text(text=script))

    return file_path


def load_prompt_template_file(prompt_file: Union[Path, str]) -> dict | str:
    """Load message templates from a file

    Args:
        prompt_file:

            * `.yaml`: Return a ``dictionary`` with all keys.
            * `other`: Return a ``string`` as system prompt.

    Returns:
         A string or a dictionary.
    """
    if prompt_file is None:
        return dict()

    if os.path.isfile(prompt_file):
        if prompt_file.endswith('.yaml'):
            with open(prompt_file, 'r') as f:
                prompt_dict = yaml.safe_load(f)
            return prompt_dict
        else:
            prompt_content = Path(prompt_file).read_text()
            return prompt_content

    return dict()


def clean_text(text: str) -> str:
    """
    Clean LLM-generated code by removing all escaping layers:
    - HTML escape (&quot;)
    - JSON double escape (\\n)
    - Python literal escape (\\\" and others)
    """

    if text is None:
        return ""

    cleaned = text

    # 1. HTML unescape (&quot;, &lt;, &gt;, &amp;)
    cleaned = html.unescape(cleaned)

    # 2. Nếu là code trong chuỗi literal → thử literal_eval
    #    Ví dụ: "\"print(\\\"hello\\\")\\n\""
    try:
        # Cố gắng biến nó thành literal Python thật
        cleaned = ast.literal_eval(f"'{cleaned}'")
    except Exception:
        pass

    # 3. JSON escape: \\n → \n ; \\" → "
    cleaned = cleaned.replace("\\n", "\n")
    cleaned = cleaned.replace("\\t", "\t")
    cleaned = cleaned.replace('\\"', '"')
    cleaned = cleaned.replace("\\'", "'")
    cleaned = cleaned.replace("\\\\", "\\")

    # 5. Xóa các ký tự HTML/escape còn sót
    cleaned = cleaned.strip()

    return cleaned
