#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from pydantic import BaseModel, Field


class BaseContext(BaseModel):

    user: str = Field(
        default='Van Minh NGUYEN',
        description='User name'
    )
