#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from langchain_core.language_models import BaseChatModel
from typing_extensions import override, Any

from src.base.agent import AgentAsNode, InputT


class CodingAgent(AgentAsNode, name='Coding'):
    """
    The Coding Agent class
    """

    @override
    def __init__(
            self,
            metadata: dict = None,
            input_schema: InputT = None,
            edges: dict[str, tuple[str]] = None,
            tool_schemas: list = None,
            output_schema: Any = None,
            model_name: str = None,
            model_provider: str = None,
            model_api_key: str = None,
            output_schema_as_tool: bool = None,
            chat_model: BaseChatModel = None,
            **kwargs
    ):
        super().__init__(
            metadata,
            input_schema,
            edges,
            tool_schemas,
            output_schema,
            model_name,
            model_provider,
            model_api_key,
            output_schema_as_tool,
            chat_model,
            **kwargs
        )

    @override
    def __call__(
            self,
            state,
            **kwargs
    ):
        # --------------- model works ---------------

        # -------------------------------------------
        return state

    def _generate_script(self):
        ...
