#
#  Copyright (c) 2026
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations

import json
import logging

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
    Literal,
    Coroutine,
    Awaitable, TypedDict, AsyncIterator, Annotated
)
from contextlib import suppress
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
from langchain.agents.middleware import (
    HumanInTheLoopMiddleware,
    PIIMiddleware,
    ModelRequest
)
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.types import Interrupt, interrupt, Command, StreamMode, All, Durability
from langgraph.typing import InputT, ContextT
from langgraph.config import RunnableConfig
from src.agent_v2.mcp_utils import get_tools
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from asyncio.queues import Queue

from src.consumer import streaming_print, streaming_yield
from src.refactory.middleware_refactory import (
    create_default_middlewares,
    create_human_in_loop_middleware,
    create_pii_middleware,
    create_todo_middleware,
    create_shell_middleware,
    create_summarize_middleware
)
from .utils import auto_validate_interrupt_tools, get_middleware_tools
from .constants import REASONING_FLAGS
from .chunk_process import process_messages_chunk, process_updates_chunk

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
logger = logging.getLogger("Agent")


class BasicAgent:
    agent_engine: CompiledStateGraph
    chat_engine: BaseChatModel
    maxlen_tool_msg: int = 500

    def __init__(
            self,
            model: str | BaseChatModel,
            tools: Sequence[Union[BaseTool, Callable, dict[str, Any]]] | None = None,
            *,
            mcp_client: Optional[MultiServerMCPClient] = None,
            provider: Optional[str] = None,
            platform: Optional[str] = None,
            api_key: Optional[str] = None,
            base_url: Optional[str] = None,
            system_prompt: str | None = None,
            middleware: Sequence[AgentMiddleware[AgentState[ResponseT], ContextT]] | Literal['default'] = (),
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

        if isinstance(model, str):
            self._chat_engine = self.initialized_chat_model(
                platform=platform,
                model=model
            )
        else:
            self._chat_engine = model

        checkpointer = checkpointer or InMemorySaver()
        store = store or InMemoryStore()

        # langchain tool
        if tools is None:
            tools = []

        # plus mcp tool
        if mcp_client:
            for tool in mcp_client.tools:
                tools.append(mcp_client.mcp_tool_to_langchain_tool(tool))

        if middleware == 'default':
            middleware: list['AgentMiddleware'] = []
            middleware.extend(create_pii_middleware())
            middleware.extend(create_todo_middleware())
            middleware.extend(create_summarize_middleware(
                base_url=self._base_url, api_key=self._api_key))
            middleware.extend(create_shell_middleware())
        elif isinstance(middleware, tuple):
            middleware = [*middleware]

        middleware_tools = get_middleware_tools(middleware)

        interrupt_on = dict()
        interrupt_on.update(auto_validate_interrupt_tools(tools))
        interrupt_on.update(auto_validate_interrupt_tools(middleware_tools))

        hil_middleware = create_human_in_loop_middleware(interrupt_on)
        middleware = middleware + hil_middleware

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

    @property
    def chat_engine(self):
        return self._chat_engine

    @property
    def agent_engine(self):
        return self._agent_engine

    def infer_model_provider(self, model_name: str):
        """Infer model provider based on model name."""
        model_name_splits = model_name.split(':')
        if len(model_name_splits) == 0:
            pass
        elif len(model_name_splits) >= 2:
            return model_name_splits[0]

        return None

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

    async def internal_astream(
            self,
            input: InputT | Command | None,
            config: RunnableConfig | None = None,
            *,
            context: ContextT | None = None,
            stream_mode: StreamMode | Sequence[StreamMode] | None = None,
            print_mode: StreamMode | Sequence[StreamMode] = (),
            output_keys: str | Sequence[str] | None = None,
            interrupt_before: All | Sequence[str] | None = None,
            interrupt_after: All | Sequence[str] | None = None,
            durability: Durability | None = None,
            subgraphs: bool = False,
            debug: bool | None = None,
            version: Literal['v1', 'v2'] = 'v2',
            consumer_queue: Optional[Queue] = None,
    ) -> AsyncIterator[dict[str, Any] | Any]:
        """Asynchronous streaming with consumer queue to put token.

        Args:
            chat_input (ChatInput): Input for a chat completion.
            consumer_queue (Queue):
                Queue consuming token generated by agent.
        """
        stream_mode = stream_mode or []
        if isinstance(stream_mode, str):
            stream_mode = [stream_mode]
        # always include updates to get interrupt information
        stream_mode = stream_mode + ['updates', ]

        local_tool_buffers = {}
        ai_message = None
        continue_as_reasoning = False

        if 'messages' in stream_mode:
            only_process_interrupt = True
        else:
            only_process_interrupt = False

        if isinstance(input, str):
            input = {"messages": [{"role": "user", "content": input}]}
        elif isinstance(input, dict):
            if 'decisions' in input:
                input = Command(resume=input)
        else:
            assert True

        chunk_streamer = self._agent_engine.astream(
            input,
            config,
            context=context,
            stream_mode=stream_mode,
            print_mode=print_mode,
            output_keys=output_keys,
            interrupt_before=interrupt_before,
            interrupt_after=interrupt_after,
            durability=durability,
            subgraphs=subgraphs,
            debug=debug,
            version=version
        )

        with suppress(Exception):
            async for chunk in chunk_streamer:
                chunk_type = chunk['type']
                if chunk_type == 'messages':
                    continue_as_reasoning = await process_messages_chunk(
                        chunk=chunk,
                        consumer_queue=consumer_queue,
                        tool_buffers=local_tool_buffers,
                        continue_as_reasoning=continue_as_reasoning
                    )
                    if ai_message is None:
                        ai_message = chunk['data']
                    else:
                        ai_message += chunk['data']
                elif chunk_type == 'updates':
                    await process_updates_chunk(chunk, consumer_queue, only_process_interrupt)

            # put None for last element to stop dequeueing
        await consumer_queue.put(None)
        return ai_message

    async def ainteract(
            self,
            input: InputT | Command | dict | None,
            config: RunnableConfig | dict | None = None,
            *,
            context: ContextT | None = None,
            stream_mode: StreamMode | Sequence[StreamMode] | None = None,
            print_mode: StreamMode | Sequence[StreamMode] = (),
            output_keys: str | Sequence[str] | None = None,
            interrupt_before: All | Sequence[str] | None = None,
            interrupt_after: All | Sequence[str] | None = None,
            durability: Durability | None = None,
            subgraphs: bool = False,
            debug: bool | None = None,
            version: Literal['v1', 'v2'] = 'v2',
            consumer_queue: Optional[Queue] = None,
            consumer_function: Optional[
                Awaitable[Callable[[Queue], None]] | Literal['print', 'yield']] = 'yield',
    ):
        """Asynchronous interact with consuming function and queue.

        Args:
            chat_input (ChatInput): Input for a chat completion.
            consumer_queue (Queue):
                Queue consuming generated token by streaming,
                then can be used by ``consumer_function`` to process element.
            consumer_function (Queue):
                The function getting consuming queue as input and process each element.
                It can be default function with 'print' and ;yield'
        """
        if consumer_queue is None:
            consumer_queue = Queue(maxsize=10000)

        gather_func = [
            self.internal_astream(
                input,
                config,
                context=context,
                stream_mode=stream_mode,
                print_mode=print_mode,
                output_keys=output_keys,
                interrupt_before=interrupt_before,
                interrupt_after=interrupt_after,
                durability=durability,
                subgraphs=subgraphs,
                debug=debug,
                version=version,
                consumer_queue=consumer_queue,
            )
        ]

        if consumer_function is None:
            pass
        elif isinstance(consumer_function, str):
            if consumer_function == 'print':
                gather_func.append(streaming_print(consumer_queue))
            elif consumer_function == 'yield':
                gather_func.append(streaming_yield(consumer_queue))
        elif isinstance(consumer_function, Callable):
            if not inspect.iscoroutine(consumer_function):
                raise RuntimeError(
                    "`consumer_function` must be coroutine."
                )
            gather_func.append(consumer_function(consumer_queue))

        out = await asyncio.gather(*tuple(gather_func))

        return out

    def interact(
            self,
            input: InputT | Command | dict | None,
            config: RunnableConfig | dict | None = None,
            *,
            context: ContextT | None = None,
            stream_mode: StreamMode | Sequence[StreamMode] | None = None,
            print_mode: StreamMode | Sequence[StreamMode] = (),
            output_keys: str | Sequence[str] | None = None,
            interrupt_before: All | Sequence[str] | None = None,
            interrupt_after: All | Sequence[str] | None = None,
            durability: Durability | None = None,
            subgraphs: bool = False,
            debug: bool | None = None,
            version: Literal['v1', 'v2'] = 'v2',
            consumer_queue: Optional[Queue] = None,
            consumer_function: Optional[
                Awaitable[Callable[[Queue], None]] | Literal['print', 'yield']] = 'yield'
    ):
        """Synchronous interact"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()

        return loop.run_until_complete(
            self.ainteract(
                input,
                config,
                context=context,
                stream_mode=stream_mode,
                print_mode=print_mode,
                output_keys=output_keys,
                interrupt_before=interrupt_before,
                interrupt_after=interrupt_after,
                durability=durability,
                subgraphs=subgraphs,
                debug=debug,
                version=version,
                consumer_queue=consumer_queue,
                consumer_function=consumer_function))
