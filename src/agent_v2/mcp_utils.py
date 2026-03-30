#
#  Copyright (c) 2026
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations
from src.mcp.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from typing import Coroutine, Any
import asyncio
import re
import json


def run(coro: Coroutine[Any, Any, Any]) -> Any:
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = asyncio.get_event_loop()

    return current_loop.run_until_complete(coro)


def get_tools(mcp_client: MultiServerMCPClient):
    tools = []
    for session in mcp_client.mcp_sessions:
        tools.extend(run(load_mcp_tools(session)))

    return tools
