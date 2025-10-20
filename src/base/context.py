#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from typing_extensions import TypedDict

from src.base.mapping import register


@register(name='shared', type='context')
class SharedContext(TypedDict):
    """This Context class provides additional information to nodes"""

    coding_task: str | None

    previous_scripts: list
