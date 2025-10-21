#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
"""
This file contains directory paths that could be used as default values
"""
import os
from pathlib import Path

import yaml

ASSETS_DIR = 'assets/'
""""""
SAVE_CRITIC_DIR = 'assets/rendered_images/critic/'
""""""
SAVE_VERIFICATION_DIR = 'assets/rendered_images/verification/'
"""sss"""

DEFAULT_CAMERA_SETTING_FILE = 'templates/camera_setting'
"""aaa"""
ANCHOR_FILE = 'assets/blender_script/anchor.py'


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
