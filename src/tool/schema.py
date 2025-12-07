#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
"""Contain args _schemas for tools"""

from pydantic import BaseModel, Field

from src.registry import RegisterToolSchema


@RegisterToolSchema(module=__name__, name='write_python_file')
class PythonFileWriteArgsSchema(BaseModel):
    """Use this schema when need writing or saving Python script/code to a file"""

    script: str = Field(..., description='The script')

    file: str = Field(..., description='the python file')


@RegisterToolSchema(module=__name__, name='execute_python_file')
class PythonFileExecuteArgsSchema(BaseModel):
    """Use this schema when need to execute a Python code file"""

    file: str = Field(..., description='the python file')


@RegisterToolSchema(module=__name__, name='bash_command')
class BashCommandArgsSchema(BaseModel):
    """Use this schema when generating bash command"""

    command: list[str] = Field(..., description='The bash command, split to list by white space')


@RegisterToolSchema(module=__name__, name='url_reader')
class UrlReaderArgsSchema(BaseModel):
    """Use this schema when need to read content in an url"""

    url: str = Field(..., description='The url need to read content')


@RegisterToolSchema(module=__name__, name='retrieve_query')
class QueryRetrieveArgsSchema(BaseModel):
    """Use this schema when need to retrieve relevant documents from vector store aligned with the query"""

    query: str = Field(..., description="The given query needing to retrieve")
