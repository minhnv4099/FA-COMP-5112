#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import logging
from typing import Any, Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from typing_extensions import override

from ..base.agent import AgentAsNode, register
from ..base.state import PlannerState
from ..base.utils import DirectionRouter
from ..utils import InputT

logger = logging.getLogger(__name__)


@register(type="agent", name='planner')
class PlannerAgent(AgentAsNode, node_name='Planner', use_model=True):
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
            template_file: str = None,
            max_subtasks: int = None,
            **kwargs
    ):
        super().__init__(
            metadata=metadata,
            input_schema=input_schema,
            edges=edges,
            tool_schemas=tool_schemas,
            output_schema=output_schema,
            model_name=model_name,
            model_provider=model_provider,
            model_api_key=model_api_key,
            output_schema_as_tool=output_schema_as_tool,
            chat_model=chat_model,
            template_file=template_file,
            **kwargs
        )
        super()._prepare_chat_template()
        self.max_subtasks = max_subtasks

    @override
    def __call__(
            self,
            state: PlannerState | dict,
            runtime: RunnableConfig = None,
            context: RunnableConfig = None,
            config: RunnableConfig = None,
            **kwargs
    ) -> Command[Literal['retriever']]:
        start_message = "-" * 50 + self.name + "-" * 50
        logger.info(start_message)
        logger.info(f"Given TASK: {state['task']}, Max subtasks: {self.max_subtasks}")
        # -------------------------------------------------
        formatted_prompt = self.chat_template.invoke(
            input={
                'task': state['task'],
                'max_subtasks': self.max_subtasks,
            })

        response, messages = self.chat_model_call(formatted_prompt)
        # -------------------------------------------------
        # logger.info(f"{len(response)} subtasks: {response}")
        self.log_conversation(logger, messages)
        end_message = "*" * (100 + len(self.name))
        logger.info(end_message)

        update_state = dict()
        update_state['coding_task'] = 'generate'
        update_state['is_sub_call'] = False
        update_state['queries'] = response
        update_state['validating_prompt'] = state['task']
        update_state['has_docs'] = False
        update_state['caller'] = 'planner'
        update_state["messages"] = messages

        # direct 'coding' agent to generate scripts
        return DirectionRouter.goto(state=update_state, node='coding', method='command')
