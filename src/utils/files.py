#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
"""
This file contains directory paths that could be used as default values
"""
import os
from pathlib import Path

ASSETS_DIR = 'assets/'


def load_prompt_template(prompt: str | Path):
    if prompt is None or not os.path.isfile(prompt):
        return prompt

    return prompt
