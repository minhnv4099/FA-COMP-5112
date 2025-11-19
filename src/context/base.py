#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from pydantic import BaseModel, Field
from dataclasses import dataclass, field


@dataclass(kw_only=True)
class BaseContext:

    user_id: str = field(
        default='1304391'
    )
