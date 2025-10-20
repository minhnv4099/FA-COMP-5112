#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from typing import Any, Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from typing_extensions import override

from ..base.agent import AgentAsNode, register, InputT
from ..base.state import PlannerState
from ..base.utils import DirectionRouter


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
            system_prompt: str = None,
            human_template: str = None,
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
            system_prompt,
            human_template,
            **kwargs
        )

    @override
    def __call__(
            self,
            state: PlannerState | dict,
            runtime: RunnableConfig = None,
            context: RunnableConfig = None,
            config: RunnableConfig = None,
            **kwargs
    ) -> Command[Literal['retriever']]:
        # -------------------------------------------------
        formatted_prompt = self._prepare_chat_prompt()
        response = self.anchor_call(formatted_prompt)
        # -------------------------------------------------
        update_state = dict()
        update_state['queries'] = response
        update_state['coding_task'] = 'generate'
        update_state['has_docs'] = False
        update_state['is_sub_call'] = False
        update_state["messages"] = {'role': "assistant", "content": "Planner Agent returned results"}
        update_state['caller'] = 'planner'

        return DirectionRouter.goto(state=update_state, node='coding', method='command')

    @override
    def anchor_call(self, formatted_prompt, *args, **kwargs):
        return ['a', 'b']

    @override
    def chat_model_call(self, task: str, *args, **kwargs):
        response = self.chat_model.invoke(task)
        tool_args = response.tool_calls[-1]['args']

        return tool_args

    @override
    def _prepare_chat_prompt(self, *args, **kwargs):
        return ''
