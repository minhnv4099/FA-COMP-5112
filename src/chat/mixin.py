#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations

import logging
from json import dumps, loads
from json.decoder import JSONDecodeError
from typing import (
    Optional,
    Union,
    Any,
    TYPE_CHECKING,
    Sequence,
    Iterable
)
from abc import ABC, ABCMeta
from abc import abstractmethod

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver

from src.types import OmegaList
from src.utils.decorator import add_note_docstring

if TYPE_CHECKING:
    from langchain_core.messages import BaseMessage, AIMessage
    from langchain_core.utils.interactive_env import is_interactive_env
    from langchain_core.tools.base import ToolCall
    from langgraph.types import StateSnapshot

logger = logging.getLogger(__name__)


class ChatMixin(ABC, metaclass=ABCMeta):
    """The Chat Mixin class acting as an LLM"""

    @classmethod
    def get_conversation(cls, messages: Sequence[BaseMessage]):
        conversation = "🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶\n"
        for m in messages:
            conversation += m.pretty_repr(is_interactive_env())
            conversation += '\n'
        conversation += '🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 🔶 ' + '\n'

        return conversation.strip()

    @classmethod
    def log_conversation(cls, _logger, conversation: Sequence[BaseMessage] | str):
        if not isinstance(conversation, str):
            conversation = cls.get_conversation(conversation)

        _logger.info(
            f"🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 CONVERSATION 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵\n{conversation}")
        _logger.info(f"🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 🔵 ")

    def _count_tokens(self, ai_message: AIMessage):
        """Accumulate input and output tokens"""
        usage_metadata = ai_message.usage_metadata
        self.num_input_tokens += usage_metadata['input_tokens']
        self.num_output_tokens += usage_metadata['output_tokens']

    def _used_token_prep(self):
        """Get a string describing input and output token usage"""
        return f'Input tokens: {self.num_input_tokens}, Output tokens: {self.num_output_tokens}'

    def _print_used_tokens(self, _logger):
        """Log input and output token usage"""
        _logger.info(self._used_token_prep())

    def _finish_session(self, _logger, conversation=None):
        if conversation:
            self.log_conversation(_logger, conversation)
        _logger.info(self._used_token_prep())
        _logger.info(self.ending_symbols)

    def __getattr__(self, item):
        if item not in self.__dict__:
            logging.critical(f"{self.__class__} has no '{item}'")


class ToolCallChatMixin(ABC, metaclass=ABCMeta):
    """The Tool Call Chat Mixin with functionalities to generate tool call and execute tool"""

    @abstractmethod
    def _internal_tool_call(
        self,
        tool_call: ToolCall,
        **kwargs,
    ) -> BaseMessage:
        """"""

    def get_pretty_prep(self, content: Any):
        """Try to get pretty content"""
        try:
            if isinstance(content, str):
                text = dumps(loads(
                    self._parse_json_content(content)), indent=4
                )
            else:
                text = dumps(content, indent=4)
            return text
        except (JSONDecodeError, TypeError) as e:
            return content

    @classmethod
    def _parse_json_content(cls, text: str):
        """Parse the structured output from text content"""
        import json, re

        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z]*", "", text).strip("` \n")
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except ValueError:
                pass

        return text

    def _combine_message(self, seq_messages: list[BaseMessage]) -> AIMessage:
        seq_repr = [
            f"Name: {m.name}\n\n{m.content}"
            for m in seq_messages
        ]

        return AIMessage(content=f'{"="*100}\n\n'.join(seq_repr))

    @classmethod
    def _convert_to_list(cls, seq: Union[Any, Iterable[Any]]) -> list[Any]:
        if seq and not isinstance(seq, OmegaList):
            seq = [seq, ]

        return seq or []


class GraphBasedMixin(ABC, metaclass=ABCMeta):
    """The Graph-Based Mixin class representing a chat using graph schema"""

    @abstractmethod
    def _build_internal_graph(self):
        """Build the internal graph"""


class StatefulChatMixin(ABC, metaclass=ABCMeta):
    """The stateful Chat Mixin class can remember the conversation"""

    def _initialize_config(self):
        self.config: RunnableConfig = RunnableConfig(
            recursion_limit=200,
            configurable={
                'thread_id': self.name
            }
        )

    def _initialize_checkpointer(self):
        self.checkpointer = InMemorySaver()

    def get_state(
        self,
        config: Optional[Union[RunnableConfig, dict]] = None
    ) -> StateSnapshot:
        return self.graph.get_state(config if config else self.config)

    def get_messages(
        self,
        config: Optional[Union[RunnableConfig, dict]] = None
    ) -> list[BaseMessage]:
        return self.get_state(config).values.get('messages', [])

    def print_conversation(
        self,
        config: Optional[Union[RunnableConfig, dict]] = None
    ):
        for m in self.get_messages(config):
            m.pretty_print()


class NonStatefulChatMixin(ABC, metaclass=ABCMeta):
    """The non-stateful Chat Mixin class only retrain everything in a call turn."""

    def _initialize_config(self):
        self.config: RunnableConfig = RunnableConfig(
            recursion_limit=200,
            configurable={
            }
        )

    def _initialize_checkpointer(self):
        self.checkpointer = False

    @add_note_docstring("No need set system prompt")
    def _set_system_behavior(self, **kwargs):
        ...

    def print_conversation(
        self,
        config: Optional[Union[RunnableConfig, dict]] = None
    ):
        logger.error(f'No checkpointer was setup [{self.checkpointer}], '
                     f'as this class is non-stateful. So no retain conversation.')

        print('===== Empty conversation =====')
