#
#  Copyright (c) 2026
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import time
import os
import asyncio
import json

from typing import Optional
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager
from src.agent_v2.base import BasicAgent
from src.mcp.client import MultiServerMCPClient
import logging

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
    while True:
        # Get data (expected dict: {"type": "...", "content": "..."})
        data = await _queue.get()

        if data is None:
            _queue.task_done()
            break

        # Standard Server-Sent Events (SSE) format
        yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

        _queue.task_done()


async def stream_llm(message: str, config):
    """
    Main orchestrator for streaming LLM responses with cancellation support.
    """
    start_time = time.time()
    flush_queue = asyncio.Queue(maxsize=10000)

    producer = asyncio.create_task(
        agent.ainteract(
            {"messages": [{"role": "user", "content": message}]},
            config,
            consumer_function=None,
            consumer_queue=flush_queue,
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
        mcp_client = MultiServerMCPClient(
            connect_params=[
                ("filesystem", 8000),
                ("gmail", 8888),
                ("contact", 8080),
                ("vision", 8765),
            ]
        )

        async with mcp_client as _mcp_client:
            agent = BasicAgent(
                'openrouter:nvidia/nemotron-3-super-120b-a12b:free',
                base_url=os.getenv('BASE_URL'),
                api_key=os.getenv('OPENROUTER_API_KEY'),
                system_prompt='Explain purpose when using a tool.',
                mcp_client=_mcp_client
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
async def chat(request: Request):
    data = await request.json()
    config = {"configurable": {"thread_id": data['thread_id']}}
    message = data["message"]

    return StreamingResponse(
        content=stream_llm(message, config),
        media_type="text/event-stream"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)
