#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from typing import Any

from pydantic import BaseModel


class AgentWithoutLLM(BaseModel):
    name: str
    """Name of the unique name/node, used to identify node in a graph"""

    metadata: dict
    """Metadata of node used to provide additional information"""

    input_schema: Any
    """Input schema the node expect"""

    edges: dict[str, tuple[str]]
    """Dictionary contains in-coming and out-going edge to and from this node"""

    tool_schemas: list
    """List of tool schemas equipped to the agent"""


class AgentAsNodeConfig(AgentWithoutLLM):
    """
    The Agent as Node Config class
    """
    output_schema: Any
    """Enforced schema so that models returns"""

    model_name: str
    """Name of model to call API"""

    model_provide: str
    """Provider of the model"""

    model_api_key: str
    """API KEY"""

    output_schema_as_tool: bool
    """Use output_schema as a tool"""

    chat_model: Any
    """Pre-defined chat mode"""
