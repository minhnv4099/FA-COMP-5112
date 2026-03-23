#
#  Copyright (c) 2026
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations
import logging

logging.getLogger("httpx").setLevel(logging.WARNING)
import sys
import random
import time
import json
from typing import (
    Any,
    Optional,
    TYPE_CHECKING,
    TypeVar,
    Union,
    Sequence,
    Callable,
    cast
)
from langchain_core.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langgraph.typing import ContextT
from langchain.agents.structured_output import (
    AutoStrategy,
    MultipleStructuredOutputsError,
    OutputToolBinding,
    ProviderStrategy,
    ProviderStrategyBinding,
    ResponseFormat,
    StructuredOutputValidationError,
    ToolStrategy,
)
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_openai.chat_models import ChatOpenAI
from langchain_core.messages import AIMessageChunk, ToolMessage

from collections import deque
from asyncio.queues import Queue
import asyncio
from functools import partial
from src.message.formated_ai import FormattedAIMessage
if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from langchain_core.tools.base import BaseTool
    from langchain.agents.middleware import AgentMiddleware
    from langchain.agents.middleware.types import AgentState
    from langgraph.cache.base import BaseCache
    from langgraph.store.base import BaseStore
    from langgraph.types import Checkpointer
    from langgraph.graph.state import CompiledStateGraph
    from langchain_core.messages.content import ReasoningContentBlock, TextContentBlock, ToolContentBlock
T = TypeVar("T")
ResponseT = TypeVar("ResponseT")


class BasicAgent:

    agent_engine: CompiledStateGraph
    chat_engine: BaseChatModel

    def __init__(
            self,
            model: str | BaseChatModel,
            tools: Sequence[BaseTool | Callable | dict[str, Any]] | None = None,
            *,
            provider: Optional[str] = None,
            api_key: Optional[str] = None,
            base_url: Optional[str] = None,
            system_prompt: str | None = None,
            middleware: Sequence[AgentMiddleware[AgentState[ResponseT], ContextT]] = (),
            response_format: ResponseFormat[ResponseT] | type[ResponseT] | None = None,
            state_schema: type[AgentState[ResponseT]] | None = None,
            context_schema: type[ContextT] | None = None,
            checkpointer: Checkpointer | None = None,
            store: BaseStore | None = None,
            interrupt_before: list[str] | None = None,
            interrupt_after: list[str] | None = None,
            debug: bool = False,
            name: str | None = None,
            cache: BaseCache | None = None,
    ):
        self.name = name or self.__class__.__name__
        if provider is None:
            provider = self.infer_model_provider(model)

        self.provider = provider
        if isinstance(model, str):
            self._chat_engine = init_chat_model(
                model=model,
                base_url=base_url,
                api_key=api_key,
            )
        else:
            self._chat_engine = model

        self._agent_engine = create_agent(
            model=self._chat_engine,
            tools=tools,
            system_prompt=system_prompt,
            middleware=middleware,
            response_format=response_format,
            state_schema=state_schema,
            context_schema=context_schema,
            checkpointer=checkpointer,
            store=store,
            interrupt_before=interrupt_before,
            interrupt_after=interrupt_after,
            debug=debug,
            name=name,
            cache=cache
        )

        self.reasoning_queue = Queue(maxsize=1000)
        self.tool_call_queue = Queue(maxsize=1000)
        self.text_queue = Queue(maxsize=1000)
        self.progression_queue = Queue(maxsize=1000)

    @property
    def chat_engine(self):
        return self._chat_engine

    @property
    def agent_engine(self):
        return self._agent_engine

    def infer_model_provider(self, model_name: str):
        """Infer model provider based on model name."""
        index = model_name.find(':')
        if index == -1:
            return None

        return model_name[:index]

    async def streaming_printer(self):
        reasoning_flusher = asyncio.create_task(
            self.flush_character(self.reasoning_queue, 'reasoning'))
        tool_call_flusher = asyncio.create_task(
            self.flush_character(self.tool_call_queue, 'tool_call_chunk'),
            name='tool_call_flusher')
        text_flusher = asyncio.create_task(
            self.flush_character(self.text_queue, 'text'),
            name='text_flusher')

        progress_writer = asyncio.create_task(
            self.flush_character(self.progression_queue)
        )

    async def flush_character(self, _queue: Queue[str], block_type: str = 'reasoning'):
        while True:
            element = await _queue.get()
            if element is None:
                break

            word = None
            for word in element.strip(' '):
                sys.stdout.write(word)
                sys.stdout.flush()
                time.sleep(random.uniform(0.003, 0.02))

            if word and not word.endswith('\n'):
                sys.stdout.write('\n')
                sys.stdout.flush()

    async def internal_astream(self, *args, **kwargs):
        current_type = None
        buffer = []

        async for chunk in self._agent_engine.astream(*args, **kwargs):
            chunk_type = chunk['type']

            if chunk_type == 'updates':
                await self.process_updates_chunk(chunk)
            elif chunk_type == 'messages':
                # handle messages dict
                pass

                for block in token.content_blocks:
                    print(block)
                    block_type = block.get("type")
                    # case 1: same type or first ever block → keep tục accumulating
                    if current_type is None or block_type == current_type:
                        current_type = block_type
                        buffer.append(block)
                        continue

                    merged_buffer = None
                    _queue = None
                    # case 2: different type → flush buffer
                    if current_type == "reasoning":
                        merged_buffer = merge_standard_block(buffer, 'reasoning')
                        _queue = self.reasoning_queue
                    elif current_type == "tool_call_chunk":
                        merged_buffer = merge_tool_call_chunk(buffer)
                        _queue = self.tool_call_queue
                    elif current_type == "text":
                        merged_buffer = merge_standard_block(buffer, 'text')
                        _queue = self.text_queue

                    if _queue is None or merged_buffer is None:
                        continue

                    await _queue.put(merged_buffer)

                    # reset buffer
                    current_type = block_type
                    buffer = [block]

        if current_type == "reasoning":
            merged_buffer = merge_standard_block(buffer, 'reasoning')
            await self.reasoning_queue.put(merged_buffer)
        elif current_type == "tool_call_chunk":
            merged_buffer = merge_tool_call_chunk(buffer)
            await self.tool_call_queue.put(merged_buffer)
        elif current_type == "text":
            merged_buffer = merge_standard_block(buffer, 'text')
            await self.text_queue.put(merged_buffer)

        await self.progression_queue.put(None)

    async def ainteract(self, *args, **kwargs):
        await asyncio.gather(
            self.internal_astream(*args, **kwargs),
            self.flush_character(self.progression_queue)
        )

    def interact(self, *args, **kwargs):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()

        loop.run_until_complete(self.ainteract(*args, **kwargs))

    async def process_updates_chunk(self, chunk: dict[str, Any]):
        data = chunk['data']
        sss = '-' * 20

        # process ai message
        if 'model' in data:
            last_message = data['model']['messages'][-1]
            last_message = FormattedAIMessage(**last_message.__dict__)

            reasoning_content = last_message.reasoning_content
            if reasoning_content:
                reasoning_content = (f"{sss} [REASONING] {sss}\n"
                                     f"{reasoning_content}"
                                     f"{sss} [REASONING] {sss}\n")
                await self.progression_queue.put(reasoning_content)

            if last_message.tool_calls:
                tool_call_str = (f"{sss} [TOOL CALLS] {sss}\n"
                                 f"{json.dumps(last_message.tool_calls, indent=2)}\n"
                                 f"{sss} [TOOL CALLS] {sss}\n")

                await self.progression_queue.put(tool_call_str)
            if last_message.content:
                await self.progression_queue.put(last_message.content)

        # process tools message
        elif 'tools' in data:
            tool_message = data['tools']['messages'][-1]
            tool_message_str = f"{sss} [TOOL MESSAGE] {sss}\n"
            tool_message_str += tool_message.pretty_repr()
            tool_message_str += '\n'
            tool_message_str += f"{sss} [TOOL MESSAGE] {sss}\n"

            await self.progression_queue.put(tool_message_str)
        else:
            print(chunk)

def merge_standard_block(blocks, block_type):
    if not blocks:
        return None

    return {
        "type": block_type,
        block_type: "".join(b.get(block_type, "") for b in blocks)
    }


def merge_tool_call_chunk(blocks: Sequence):
    tool_call = {
        "id": None,
        "name": None,
        "args": "",
        "index": None,
    }

    for b in blocks:
        if b.get("id"):
            tool_call["id"] = b["id"]
        if b.get("name"):
            tool_call["name"] = b["name"]
        if b.get("args"):
            tool_call["args"] += b["args"]
        if b.get("index") is not None:
            tool_call["index"] = b["index"]

    return tool_call


def format_tool_call_log(tool_call):
    return f"[TOOL] {tool_call.get('name')} | args={tool_call.get('args')}"