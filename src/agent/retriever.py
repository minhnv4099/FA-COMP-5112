#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations

import logging
from typing import (
    Literal,
    Union,
    Generic,
    Optional,
    TYPE_CHECKING,
    cast,
    Any
)
from typing_extensions import override

from langchain_core.messages import SystemMessage, AIMessage
from langchain_core.prompts import SystemMessagePromptTemplate
from langgraph.graph.state import END
from langgraph.config import RunnableConfig
from langgraph.runtime import Runtime
from langgraph.types import Command

from src.registry import RegisterNode, RegisterAgent
from src.utils import DirectionRouter
from src.typing import StateT, ContextT, InputT, OutputT
from src.node.base import BaseNode
from src.utils.decorator import add_note_docstring

if TYPE_CHECKING:
    from src.state.comp_5112 import RetrieverState
    from src.message.parsed_tool_call import ParsedTollCallMessage

logger = logging.getLogger(__name__)


@add_note_docstring(docs="'COMP-5112' project")
@RegisterAgent(module=__name__, name='retriever')
@RegisterNode(module=__name__, name='retriever')
class RetrieverAgent(
    BaseNode,
    Generic[StateT, ContextT, InputT, OutputT],
    node_name="Retriever",
    use_model=True
):
    """The Retriever Agent class"""

    @add_note_docstring("Used for only COMP 5112")
    @override
    def __call__(
        self,
        state: StateT,
        config: Optional[RunnableConfig] = None,
        *,
        runtime: Optional[Runtime[ContextT]] = None,
        **kwargs
    ) -> Command[Literal['coding']]:
        """"""
        logger.info(self.opening_symbols)
        self.persistent_on_invoke = True

        retrieved_docs: dict[int, Any] = dict()

        queries = state.get('agent_response', [])
        for i, query in enumerate(queries):
            separator = '\n' if state['coding_task'] == 'fix' else ''
            logger.info(f"query {i + 1}/{len(queries)}: {separator}{query}")

            selected_system_prompt = self._select_system_prompt()
            prompt_template = self._prepare_chat_template(
                system_template=selected_system_prompt,
                human_template=self.human_template
            )

            prompt_value = prompt_template.invoke(
                input={'query': query}
            )

            response = cast(
                "ParsedTollCallMessage",
                self.invoke(
                    input=prompt_value,
                    config=self.config
                )
            )

            agent_response = response.get_field(field='summary', default="No instruction")
            retrieved_docs[i] = {
                'query': query,
                'instruction': agent_response
            }

        # logger.info('Aggregate messages')
        # aggr_prompt = [self._get_aggregate_system_prompt()] + self.get_messages()
        # aggr_message = self.invoke(
        #     input=aggr_prompt,
        #     config=self.config
        # )

        update_state = {
            'agent_response': retrieved_docs,
            'coding_task': state.get('coding_task', 'generate'),
            'caller': state.get('caller', 'planner'),
            'messages': self.get_messages()
        }

        self._finish_session(_logger=logger)

        # return update_state
        return DirectionRouter.jump(
            updates=update_state,
            jump_to='coding',
            method='command'
        )

    def _select_system_prompt(self) -> Union[SystemMessage, SystemMessagePromptTemplate]:
        return self.system_template

    def _get_aggregate_system_prompt(self):
        return SystemMessage(
            content='Aggregate and summarize the conversation.'
        )
