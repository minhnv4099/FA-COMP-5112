#
#  Copyright (c) 2026
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import time
import os
import asyncio
import json
import logging

from typing import Optional
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.agent_v2.base import BasicAgent
from src.mcp.client import MultiServerMCPClient
from src.consumer import streaming_yield
from src.mcp.manager import auto_create_mcp_client
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("ChatApp")
mcp_client: Optional[MultiServerMCPClient] = None
agent: Optional[BasicAgent] = None


async def flush_character(_queue: asyncio.Queue):
    """
    Retrieves data from the Queue (populated by LLM/Process_chunk)
    and yields it as a stream for FastAPI's StreamingResponse.
    """
    async for data in streaming_yield(_queue):
        yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def stream_llm(message: str | dict, config):
    """
    Main orchestrator for streaming LLM responses with cancellation support.
    """
    start_time = time.time()
    flush_queue = asyncio.Queue(maxsize=10000)

    producer = asyncio.create_task(
        agent.ainteract(
            message,
            config,
            stream_mode='messages',
            consumer_queue=flush_queue,
            consumer_function=None,
        )
    )

    try:
        # Stream data to the frontend
        async for token in flush_character(flush_queue):
            yield token

    except asyncio.CancelledError:
        # This block is triggered if the client disconnects (FastAPI raises CancelledError)
        print("Client disconnected. Cancelling LLM producer...")
        raise  # Re-raise to let FastAPI handle the cleanup

    finally:
        if not producer.done():
            producer.cancel()  # Signal the producer to stop immediately
            try:
                # Wait for the producer to acknowledge the cancellation
                await producer
            except asyncio.CancelledError:
                # This is the expected behavior when a task is cancelled
                logger.info("Producer task successfully cancelled.")
            except Exception as e:
                logger.info(f"Error during producer cleanup: {e}")

        logger.info(f'Total processing time: {time.time() - start_time:.2f} seconds')


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global agent, mcp_client
    try:
        async with auto_create_mcp_client() as _mcp_client:
            agent = BasicAgent(
                'openrouter:nvidia/nemotron-3-super-120b-a12b:free',
                # 'deepseek-ai/DeepSeek-R1-0528',
                # platform='huggingface-endpoint',
                # system_prompt='Explain purpose when using a tool.',
                base_url=os.getenv('BASE_URL'),
                api_key=os.getenv('OPENROUTER_API_KEY'),
                mcp_client=_mcp_client,
                middleware='default'
            )

            yield
    except KeyboardInterrupt:
        pass
    finally:
        # Cleanup khi tắt server
        logger.info("App shutdown.")


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def home_page():
    return FileResponse(os.path.join("static", "index.html"))


@app.post("/chat")
async def chat(data: Request):
    payload = await data.json()

    config = {"configurable": {"thread_id": payload.get('thread_id')}}
    if 'message' in payload:
        message: str = payload['message']
    else:
        decisions = [
            {
                'type': payload['decision'],
                'message': payload.get('additional_info'),
                'edited_action': payload.get('additional_info')
            }
        ]
        message: dict = {
            'decisions': decisions
        }

    return StreamingResponse(
        content=stream_llm(message, config),
        media_type="text/event-stream"
    )
