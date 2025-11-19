#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
"""The React agent inherits the base agent with additional re-look to check
if it can provide the final response
"""

from __future__ import annotations

import logging
from typing import Optional, Union, TYPE_CHECKING, Generic, Literal, Sequence

from langchain_core.prompt_values import PromptValue
from typing_extensions import override

from langchain_core.runnables import RunnableConfig
from langchain_core.messages import BaseMessage
from langgraph.runtime import Runtime

from src.registry import RegisterAgent
from src.types import StateT, ContextT, OutputT, ToolSchema
from src.chat.mixin import NonStatefulChatMixin
from src.agent.mixin import ReactAgentMixin
from src.chat.stateful_chat import ToolCallExecuteStatefulChat

if TYPE_CHECKING:
    ...

logger = logging.getLogger(__name__)


@RegisterAgent(module_path=__name__, name='react_agent')
class LoopReactAgent(
    NonStatefulChatMixin,
    ReactAgentMixin,
    ToolCallExecuteStatefulChat,
    Generic[StateT, ContextT, OutputT, ToolSchema]
):
    """"The ReAct Agent can action and observe until meet conditions. It's non-stateful"""

    @override
    def invoke(
        self,
        input: Union[str, PromptValue, BaseMessage, Sequence[BaseMessage]],
        config: Optional[Union[RunnableConfig, dict]] = None,
        *,
        context: Optional[Runtime[ContextT]] = None,
        **kwargs,
    ) -> BaseMessage:
        prompt = self.chat_template.invoke(
            input=input,
            config=config
        )

        return super().invoke(
            input=prompt,
            config=config,
            context=context
        )


@RegisterAgent(module_path=__name__, name='react_stateful_agent')
class ReactStatefulAgent(
    ReactAgentMixin,
    ToolCallExecuteStatefulChat,
    Generic[StateT, ContextT, OutputT, ToolSchema]
):
    """"""
