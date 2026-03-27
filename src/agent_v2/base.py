#
#  Copyright (c) 2026
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations
import logging

import sys
import random
import json
import inspect
import asyncio

from typing import (
    Any,
    Optional,
    TYPE_CHECKING,
    TypeVar,
    Union,
    Sequence,
    Callable,
    cast,
    Literal,
    Coroutine,
    Awaitable
)
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
from langchain_core.messages import AIMessageChunk, ToolMessage, AIMessage
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.types import Interrupt, interrupt, Command
from langgraph.config import RunnableConfig
from src.agent_v2.mcp_utils import get_tools
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from asyncio.queues import Queue

from src.consumer import streaming_print, streaming_yield
from .utils import auto_validate_interrupt_tools

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
    from src.mcp.client import MultiServerMCPClient

logging.getLogger("httpx").setLevel(logging.WARNING)
T = TypeVar("T")
ResponseT = TypeVar("ResponseT")


class BasicAgent:
    agent_engine: CompiledStateGraph
    chat_engine: BaseChatModel
    maxlen_tool_msg: int = 500

    def __init__(
            self,
            model: str | BaseChatModel,
            tools: Sequence[BaseTool | Callable | dict[str, Any]] | None = None,
            *,
            mcp_client: Optional[MultiServerMCPClient] = None,
            provider: Optional[str] = None,
            platform: Optional[str] = None,
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
        if provider is None and isinstance(model, str):
            provider = self.infer_model_provider(model)

        self.provider = provider
        self._base_url = base_url
        self._api_key = api_key

        # process chat model
        if isinstance(model, str):
            self._chat_engine = self.initialized_chat_model(
                platform=platform,
                model=model
            )
        else:
            self._chat_engine = model

        # process tools (langchain + mcp)
        if tools is None:
            tools = []

        if mcp_client:
            for tool in mcp_client.tools:
                tools.append(mcp_client.mcp_tool_to_langchain_tool(tool))

        # auto_interrupt_before, auto_interrupt_after = auto_validate_interrupt_tools(tools)
        # interrupt_before = interrupt_before or auto_interrupt_before
        # interrupt_after = interrupt_after or auto_interrupt_after

        checkpointer = checkpointer or InMemorySaver()
        store = store or InMemoryStore()

        if not middleware and False:
            middleware = [
                HumanInTheLoopMiddleware(
                    interrupt_on={
                        "write_file": True,  # All decisions (approve, edit, reject) allowed
                        "list_files": {"allowed_decisions": ["approve", "reject"]},  # No editing allowed
                        # Safe operation, no approval needed
                        "read_data": True,
                    },
                    # Prefix for interrupt messages - combined with tool name and args to form the full message
                    # e.g., "Tool execution pending approval: execute_sql with query='DELETE FROM...'"
                    # Individual tools can override this by specifying a "description" in their interrupt config
                    description_prefix="Tool execution pending approval",
                ),
            ]

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

    def initialized_chat_model(
            self,
            platform: str,
            model: str,
    ):
        if platform == 'huggingface-endpoint':
            from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
            llm = HuggingFaceEndpoint(
                repo_id=model,
                task="text-generation",
                max_new_tokens=512,
                do_sample=False,
                repetition_penalty=1.03,
                provider="auto",
            )

            return ChatHuggingFace(llm=llm)

        elif platform == 'huggingface-pipeline':
            from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline

            llm = HuggingFacePipeline.from_model_id(
                model_id=model,
                task='tex-generation')

            return ChatHuggingFace(llm=llm)

        else:
            return init_chat_model(
                model=model,
                base_url=self._base_url,
                api_key=self._api_key,
            )

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

    async def internal_astream(
            self,
            input: dict | Command | None,
            config: RunnableConfig | None = None,
            *args,
            context: Optional[Any] = None,
            stream_mode: Optional[list[str]] = None,
            consumer_queue: Optional[Queue] = None,
            **kwargs
    ):
        """Asynchronous streaming with consumer queue to put token.

        Args:
            consumer_queue (Queue):
                Queue consuming token generated by agent.
        """
        chunk_streamer = self._agent_engine.astream(
            input,
            config,
            *args,
            context=context,
            stream_mode=stream_mode,
            **kwargs
        )
        local_tool_buffers = {}
        ai_message = None

        async for chunk in chunk_streamer:
            chunk_type = chunk['type']
            if chunk_type == 'messages':
                await self.process_messages_chunk(
                    chunk,
                    consumer_queue,
                    local_tool_buffers
                )
                if ai_message is None:
                    ai_message = chunk['data']
                    continue
                ai_message += chunk['data']
            elif chunk_type == 'updates':
                await self.process_updates_chunk(chunk, consumer_queue)

        # put None for last element to stop dequeueing
        await consumer_queue.put(None)
        return ai_message

    async def ainteract(
            self,
            *args,
            consumer_queue: Optional[Queue] = None,
            consumer_function: Optional[
                Awaitable[Callable[[Queue], None]] | Literal['print', 'yield']] = 'yield',
            **kwargs
    ):
        """Asynchronous interact with consuming function and queue.

        Args:
            consumer_queue (Queue):
                Queue consuming generated token by streaming,
                then can be used by ``consumer_function`` to process element.
            consumer_function (Queue):
                The function getting consuming queue as input and process each element.
                It can be default function with 'print' and ;yield'
        """
        kwargs.setdefault('version', 'v2')
        kwargs.setdefault('stream_mode', ['messages'])

        if consumer_queue is None:
            consumer_queue = Queue(maxsize=10000)

        gather_func = [self.internal_astream(*args, consumer_queue=consumer_queue, **kwargs)]

        if consumer_function is None:
            pass
        elif isinstance(consumer_function, str):
            if consumer_function == 'print':
                gather_func.append(streaming_print(consumer_queue))
            elif consumer_function == 'yield':
                gather_func.append(streaming_print(consumer_queue))
        elif isinstance(consumer_function, Callable):
            if not inspect.iscoroutine(consumer_function):
                raise RuntimeError(
                    "`consumer_function` must be coroutine."
                )
            gather_func.append(consumer_function(consumer_queue))

        out = await asyncio.gather(*tuple(gather_func))

        return out

    def interact(self, *args, **kwargs):
        """Synchronous interact"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()

        return loop.run_until_complete(self.ainteract(*args, **kwargs))

    async def process_updates_chunk(
            self,
            chunk: dict[str, Any],
            consumer_queue: asyncio.Queue,
    ):
        data = chunk['data']

        if "__interrupt__" in data:
            pass
            # (Interrupt(value={
            #     'action_requests':
            #         [
            #             {'name': 'list_files', 'args': {'directory': 'src/agent'},
            #              'description': "Tool execution pending approval\n\nTool: list_files\nArgs: {'directory': 'src/agent'}"}
            #         ],
            #         'review_configs': [
            #             {'action_name': 'list_files', 'allowed_decisions': ['approve', 'reject']}
            #         ]},
            #            id='1ebaba73cfa658e5f4a06638e8927228'))

            # process ai message
        if 'model' in data:
            last_message: "AIMessage" = data['model']['messages'][-1]

            for block in last_message.content_blocks:
                block_type = block.get("type")

                if block_type == 'reasoning':
                    await consumer_queue.put({
                        "type": "reasoning",
                        "content": block.get('reasoning', '')
                    })

                elif block_type == 'text':
                    await consumer_queue.put({
                        "type": "text",
                        "content": block.get('text', '')
                    })

                elif block_type == 'tool_call':
                    try:
                        clean_args = json.loads(json.dumps(block["args"])) if block["args"] else {}
                    except json.JSONDecodeError:
                        clean_args = block["args"]

                    tool_call_content = {
                        "id": block["id"],
                        "name": block["name"],
                        "args": clean_args
                    }
                    formatted_tool = {
                        "type": "tool_call",
                        "content": tool_call_content
                    }

                    await consumer_queue.put(formatted_tool)

        # process tools message
        elif 'tools' in data:
            tool_messages: list[ToolMessage] = data['tools']['messages']
            for tool_message in tool_messages:
                await consumer_queue.put({
                    "type": "tool_result",
                    "content": tool_message.content
                })

        else:
            pass

    async def process_messages_chunk(
            self,
            chunk: dict[str, Any],
            progression_queue: asyncio.Queue,
            tool_buffers: dict
    ):
        token: AIMessageChunk | ToolMessage = chunk['data'][0]

        if isinstance(token, ToolMessage):
            content = token.content if isinstance(token.content, str) else str(token.content)
            await progression_queue.put({
                "type": "tool_result",
                "content": content
            })
            return

        for block in token.content_blocks:
            block_type = block.get("type")

            if block_type == 'reasoning':
                await progression_queue.put({
                    "type": "reasoning",
                    "content": block.get('reasoning', '')
                })

            elif block_type == 'text':
                await progression_queue.put({
                    "type": "text",
                    "content": block.get('text', '')
                })

            elif block_type == 'tool_call_chunk':
                # case 1: same type or first ever block → keep accumulating
                idx = block.get("index")
                if idx not in tool_buffers:
                    tool_buffers[idx] = {"id": "", "name": "", "args": "", "index": idx}

                # update tool call chunk into buffer
                if block.get("id"):
                    tool_buffers[idx]["id"] = block["id"]
                if block.get("name"):
                    tool_buffers[idx]["name"] = block["name"]
                if block.get("args"):
                    tool_buffers[idx]["args"] += block["args"]
                if block.get("index"):
                    tool_buffers[idx]["index"] = block["index"]

            # 3. Kiểm tra xem Tool Call đã hoàn thiện chưa (thường dựa vào việc kết thúc chunk stream)
            # Trong LangGraph/LangChain, khi tool_call_chunk không còn tới nữa, ta flush nó ra
        if not getattr(token, 'tool_call_chunks'):
            await self._flush_tool_buffers(progression_queue, tool_buffers)

    async def _flush_tool_buffers(self, progression_queue: Queue, tool_buffers: dict):
        """Hàm phụ trợ để put kết quả tool call đã gộp ra queue"""
        if not tool_buffers:
            return

        for idx, tool in tool_buffers.items():
            try:
                clean_args = json.loads(tool["args"]) if tool["args"] else {}
            except json.JSONDecodeError:
                # Phòng trường hợp stream bị cắt ngang làm JSON lỗi
                clean_args = tool["args"]

            tool_content = {
                "id": tool["id"],
                "name": tool["name"],
                "args": clean_args  # Lúc này args đã là string JSON hoàn chỉnh
            }
            formatted_tool = {
                "type": "tool_call",
                "content": tool_content  # Lúc này args đã là string JSON hoàn chỉnh
            }
            # In ra dưới dạng JSON đẹp
            await progression_queue.put(formatted_tool)

        tool_buffers.clear()  # Xóa buffer sau khi đã in


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
