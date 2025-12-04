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
    Union,
    Literal,
    Any
)
from typing_extensions import override

from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from langgraph.types import Command

from src.registry import RegisterNode, RegisterAgent
from src.typing import InputT, StateT, OutputT, ContextT
from src.utils import DirectionRouter
from src.node.base import BaseNode
from src.utils.decorator import add_note_docstring

if TYPE_CHECKING:
    from langchain_core.messages import SystemMessage
    from langchain_core.prompts import SystemMessagePromptTemplate
    from src.message.parsed_tool_call import ParsedTollCallMessage

logger = logging.getLogger(__name__)


@add_note_docstring(docs="Used for only 'COMP-5112' project")
@RegisterAgent(module=__name__, name='planner')
@RegisterNode(module=__name__, name='planner')
class PlannerAgent(
    BaseNode,
    Generic[StateT, ContextT, InputT, OutputT],
    node_name='Planner',
    use_model=True
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
        state: StateT,
        config: Optional[RunnableConfig] = None,
        *,
        runtime: Optional[Runtime[ContextT]] = None,
        **kwargs
    ) -> Command[Literal['retriever']]:
        """"""
        logger.info(self.opening_symbols)
        self.persistent_on_invoke = True

        logger.info(f"Task: {state['task']}")
        # -------------------------------------------------
        selected_system_prompt = self._select_system_prompt()
        prompt_template = self._prepare_chat_template(
            system_template=selected_system_prompt,
            human_template=self.human_template
        )
        prompt_value = prompt_template.invoke(
            input={
                'task': state['task'],
                'max_subtasks': self.max_subtasks
            }
        )

        response = cast(
            "ParsedTollCallMessage",
            self.invoke(
                input=prompt_value,
                config=self.config
            )
        )

        agent_response = response.get_field(field='subtasks', default=[])
        logger.info(f'Number of subtasks: {len(agent_response)}')

        update_state = dict()
        update_state["agent_response"] = agent_response
        update_state["subtasks"] = agent_response
        update_state['coding_task'] = 'generate'
        update_state['validating_prompt'] = state['task']
        update_state['caller'] = 'planner'
        update_state["messages"] = self.get_messages()

        self._finish_session(logger)

        return DirectionRouter.jump(
            updates=update_state,
            method='command',
            jump_to='retriever'
        )

    def _select_system_prompt(self) -> Union[SystemMessage, SystemMessagePromptTemplate]:
        return self.system_template
