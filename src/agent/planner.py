#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations

import logging
from typing import (
    Generic,
    Optional,
    TYPE_CHECKING,
    cast,
    Any
)
from typing_extensions import override

from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import END
from langgraph.runtime import Runtime
from langgraph.types import Command

from src.registry import RegisterNode, RegisterAgent
from src.types import InputT, StateT, OutputT, ContextT
from src.state.comp_5112 import PlannerState
from src.node.base import BaseNode
from src.base.utils import DirectionRouter
from src.utils.decorator import add_note_docstring

if TYPE_CHECKING:
    from src.message.parsed_tool_call import ParsedTollCallMessage

logger = logging.getLogger(__name__)


@add_note_docstring(docs="Used for only 'COMP-5112' project")
@RegisterAgent(module_path=__name__, name='planner')
@RegisterNode(module_path=__name__, name='planner')
class PlannerAgent(
    BaseNode,
    Generic[StateT, ContextT, InputT, OutputT],
    node_name='Planner', use_model=True
):
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

    @add_note_docstring('For COMP 5112 project')
    @override
    def __call__(
        self,
        state: PlannerState,
        runtime: Optional[Runtime[ContextT]] = None,
        config: Optional[RunnableConfig] = None,
        **kwargs
    ) -> OutputT | Command:
        """"""
        config = self.config

        logger.info(self.opening_symbols)
        logger.info(f"Message: {state['task']}")
        # -------------------------------------------------
        formatted_prompt = self.human_template.format(
            task=state['task'],
            max_subtasks=self.max_subtasks,
        )
        # -------------------------------------------------
        # message = cast("ParsedTollCallMessage", self.invoke(
        #     input=formatted_prompt,
        #     # NOTE: use own config
        #     config=config
        # ))
        #
        # response = self.process_response(self.get_desired_result(
        #     message=message,
        #     keys_to_get='subtasks',
        #     default=[]
        # ))
        # response = [f"{state['task']}. {r}" for r in response]
        # messages = self.get_messages(config)
        # -------------------------------------------------
        response = [state['task']]
        messages = [state['task']]

        self._finish_session(logger)

        update_state = dict()
        update_state['coding_task'] = 'generate'
        update_state['is_sub_call'] = False
        update_state['queries'] = response
        update_state['validating_prompt'] = state['task']
        update_state['has_docs'] = False
        update_state['caller'] = 'planner'
        update_state["messages"] = messages

        # direct 'coding' agent to generate scripts
        return DirectionRouter.goto(state=update_state, node='retriever', method='command')
