#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations
import uuid

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
from typing_extensions import override, deprecated

from langchain_core.messages import SystemMessage
from langchain_core.prompts import SystemMessagePromptTemplate
from langgraph.graph.state import END
from langgraph.config import RunnableConfig
from langgraph.runtime import Runtime
from langgraph.types import Command

from src.registry import RegisterNode, RegisterAgent
from src.utils import DirectionRouter
from src.types import StateT, ContextT, InputT, OutputT
from src.node.base import BaseNode
from src.utils.decorator import add_note_docstring

if TYPE_CHECKING:
    from src.state.comp_5112 import RetrieverState

logger = logging.getLogger(__name__)


@add_note_docstring(docs="'COMP-5112' project")
@RegisterAgent(module_path=__name__, name='retriever')
@RegisterNode(module_path=__name__, name='retriever')
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
        state: RetrieverState,
        config: Optional[RunnableConfig] = None,
        *,
        runtime: Optional[Runtime[ContextT]] = None,
        **kwargs
    ) -> Union[OutputT, Command, dict[str, Any]]:
        """"""
        logger.info(self.opening_symbols)
        self.config['configurable']['thread_id'] = uuid.uuid1()

        retrieved_docs: dict[int, list] = dict()

        for i, query in enumerate(state['queries']):
            logger.info(f"query {i + 1}/{len(state['queries'])}: {query}")

            selected_system_prompt = self._select_system_prompt()
            prompt_value = self._prepare_chat_template(
                system_prompt=selected_system_prompt,
                human_template=self.human_template
            ).invoke(input=query)

            response = self.invoke(
                input=prompt_value,
                config=self.config
            )

            retrieved_docs[i] = response.content

        # -------------------------------------------------
        logger.info('Aggregate the conversion')
        aggr_prompt = [self._get_aggregate_system_prompt()] + self.get_messages()
        final_message = self.invoke(
            input=aggr_prompt,
            config=self.config
        )

        update_state = {
            'retrieved_docs': retrieved_docs,
            "messages": final_message,
            'queries': state['queries'],
        }

        # return update_state
        return DirectionRouter.goto(state=update_state, node=END, method='command')

    def _select_system_prompt(self) -> Union[SystemMessage, SystemMessagePromptTemplate]:
        return self.system_template

    def _get_aggregate_system_prompt(self):
        return SystemMessage(
            content='Aggregate and summarize the conversation.'
        )
