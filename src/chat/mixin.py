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

from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.utils.interactive_env import is_interactive_env
from langgraph.checkpoint.memory import InMemorySaver

from src.typing import ListLike
from src.utils.decorator import add_note_docstring

if TYPE_CHECKING:
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

    def _finish_session(self, _logger, conversation=None):
        if conversation:
            self.log_conversation(_logger, conversation)
        _logger.info(self._used_token_prep())
        _logger.info(self.closing_symbols)
        self.num_input_tokens = 0
        self.num_output_tokens = 0


class ToolCallChatMixin(ABC, metaclass=ABCMeta):
    """The Tool Call Chat Mixin with functionalities to generate tool call and execute tool"""

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
        import re

        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z]*", "", text).strip("` \n")
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return loads(match.group())
            except ValueError:
                pass

        return text

    def _combine_message(self, *seq_messages: BaseMessage) -> AIMessage:
        """Combine messages to a single AI Message with details of an AI message that has tool calls.
        It takes a tool-call AI message and tool messages, create a new AI message with these details. \n
        It's really useful with tool calls. Optionally, it can be used to change a format printed of a message.
        """
        seq_repr = []
        for m in seq_messages:
            repr_content = ""
            if not (name := m.name):
                name = '<NO NAME>'
            repr_content += f'- Name: {name}\n\n'

            if not (content := m.content):
                content = '<EMPTY>'
            repr_content += f'- Content: {content}\n\n'

            # Only AIMessage has tool calls
            if isinstance(m, AIMessage):
                if m.tool_calls:
                    repr_content += f"- Tool Calls: {dumps(m.tool_calls, indent=3)}\n"

            seq_repr.append(repr_content)

        ai_content = "Details of ai message with tool calls: \n\n" + f'{"-"*60}\n\n'.join(seq_repr)
        return AIMessage(content=ai_content)

    @classmethod
    def _convert_to_list(cls, seq: Union[Any, Iterable]) -> list[Any]:
        if seq and not isinstance(seq, ListLike):
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
        print(self.opening_symbols)
        print('>>>>>>>> CONVERSATION <<<<<<<<')
        print()
        for m in self.get_messages(config):
            m.pretty_print()

        print()
        print(self._used_token_prep())
        print(self.closing_symbols)


class NonStatefulChatMixin(ABC, metaclass=ABCMeta):
    """The non-stateful Chat Mixin class only retrain everything in a call turn."""

    @add_note_docstring("No need set system prompt")
    def _set_system_behavior(self, **kwargs):
        ...
