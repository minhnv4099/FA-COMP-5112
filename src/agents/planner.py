#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from typing import Optional, Any, Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from langgraph.types import Command
from typing_extensions import override

from src.base.agent import AgentAsNode, register, InputT
from src.base.context import SharedContext
from src.base.state import PlannerState


@register(type="agent", name='planner')
class PlannerAgent(AgentAsNode, name='Planner', use_model=True):
    """
    The Planner Agent class
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

    def anchor_call(self):
        return ['a', 'b']

    @override
    def __call__(
            self,
            state: PlannerState | dict,
            runtime: Optional[Runtime[RunnableConfig]] = None,
            context: Optional[Runtime] = None,
            config: Optional[Runtime[SharedContext]] = None,
            **kwargs
    ) -> Command[Literal['retriever']]:
        # -------------------------------------------------
        # response = self.chat_model.invoke(state['task'])
        # tool_args = response.tool_calls[-1]['args']
        # -------------------------------------------------
        update_state = dict()
        update_state['queries'] = self.anchor_call()
        update_state['has_docs'] = False
        update_state["messages"] = {'role': "assistant", "content": "Planner Agent returned results"}
        update_state['coding_task'] = 'generate'

        return Command(
            update=update_state,
            goto='coding'
        )
