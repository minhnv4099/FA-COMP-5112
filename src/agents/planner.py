#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from typing import Optional, Any

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from typing_extensions import override

from src.base.agent import AgentAsNode, InputT
from src.base.state import PlannerState


class PlannerAgent(AgentAsNode, name='Planner'):
    """
    The Planner Agent class
    """

    @override
    def __init__(self, metadata: dict = None, input_schema: InputT = None,
                 edges: dict[str, tuple[str]] = None, tool_schemas: list = None, output_schema: Any = None,
                 model_name: str = None, model_provider: str = None, model_api_key: str = None,
                 output_schema_as_tool: bool = None, chat_model: BaseChatModel = None, **kwargs):
        super().__init__(metadata, input_schema, edges, tool_schemas, output_schema, model_name, model_provider,
                         model_api_key, output_schema_as_tool, chat_model, **kwargs)

        self.validate_model()
        self.validate_schema()

    @override
    def __call__(
            self,
            state: PlannerState | dict,
            config: Optional[RunnableConfig] = None,
            context=None,
            runtime: Runtime = None,
            **kwargs
    ):
        # -------------------------------------------------
        return self.chat_model.invoke(state['task'])
        # -------------------------------------------------
