#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
"""Contain args schemas for tools"""

from pydantic import Field

from src.registry import RegisterToolSchema
from src.tool.base import BaseToolSchema


@RegisterToolSchema(module_path=__name__, name='write_python_file_schema')
class PythonFileWriteArgsSchema(BaseToolSchema):
    """Use this schema when need writing or saving Python script/code to a file"""

    script: str = Field(..., description='The script')

    file: str = Field(..., description='the python file')


@RegisterToolSchema(module_path=__name__, name='execute_python_file_schema')
class PythonFileExecuteArgsSchema(BaseToolSchema):
    """Use this schema when need to execute a Python code file"""

    file: str = Field(..., description='the python file')


@RegisterToolSchema(module_path=__name__, name='bash_command_schema')
class BashCommandArgsSchema(BaseToolSchema):
    """Use this schema when generating bash command"""

    command: list[str] = Field(..., description='The bash command, split to list by white space')


@RegisterToolSchema(module_path=__name__, name='read_url_schema')
class UrlReaderArgsSchema(BaseToolSchema):
    """Use this schema when need to read content in an url"""

    url: str = Field(..., description='The url need to read content')


@RegisterToolSchema(module_path=__name__, name='retrieve_query_schema')
class QueryRetrieveArgsSchema(BaseToolSchema):
    """Use this schema when need to retrieve relevant documents from vector store aligned with the query"""

    query: str = Field(..., description="The given query needing to retrieve")
