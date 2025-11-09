#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import logging
from typing import Literal, Generic
from typing_extensions import override

from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from langgraph.types import Command

from src.registry import RegisterNode, RegisterAgent
from src.types import InputT, StateT, OutputT, ContextT
from src.base.node import AgentAsNode
from src.base.state import PlannerState
from src.base.utils import DirectionRouter
from src.utils.decorator import add_note_docstring

logger = logging.getLogger(__name__)


@add_note_docstring(docs="Used for only 'COMP-5112' project")
@RegisterAgent(module_path=__name__, name='planner')
@RegisterNode(module_path=__name__, name='planner')
class PlannerAgent(AgentAsNode, Generic[StateT, ContextT, InputT, OutputT], node_name='Planner', use_model=True):
    """The Planner Agent class"""

    @override
    def __init__(
        self,
        *args,
        max_subtasks: int = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.max_subtasks = max_subtasks

    @override
    def __call__(
        self,
        state: PlannerState | dict,
        runtime: Runtime[ContextT] = None,
        config: RunnableConfig = None,
        **kwargs
    ) -> OutputT | Command[Literal['coding']]:
        """"""

        logger.info(self.opening_symbols)
        logger.info(f"TASK: {state['task']}, Max subtasks: {self.max_subtasks}")
        # -------------------------------------------------
        formatted_prompt = self._get_pretty_formatted_prompt(
            chat_prompt_template=self.chat_template,
            input={
                'task': state['task'],
                'max_subtasks': self.max_subtasks,
            }
        )

        response, messages = self.chat_model_call(formatted_prompt)
        # -------------------------------------------------
        # response = [state['task']]
        # messages = [state['task']]
        logger.info(f"Number of delegated subtasks: {len(response)}")

        self._finish_session(logger, messages)

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
