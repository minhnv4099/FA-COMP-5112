#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from pydantic import BaseModel, Field
from typing import Literal
from src.registry import RegisterChatOutputSchema


class RetrievingCategory(BaseModel):
    """Always use this schema when need to classify the query that may be used in various purposes.
    For example, to fix, to create, to enhance or just look up information, etc.
    """

    category: Literal[
        'fix',
        'create',
        'enhance',
        'search',
        'greeting'
    ] = Field(
        ...,
        examples=['search', 'enhance'],
        description='The category of purpose based on the query'
    )
