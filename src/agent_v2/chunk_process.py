#
#  Copyright (c) 2026
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations

from typing import Any
import re
import asyncio
import json
from langchain_core.messages import AIMessageChunk, AIMessage, ToolMessage
from .constants import REASONING_FLAGS


def split_reasoning_text(content: str, start_flag: str = "<think>", end_flag: str = "</think>"):
    # used for updates chunk
    if start_flag in content and end_flag in content:
        pattern = rf"{start_flag}(.*?){end_flag}(.*)"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip(), match.group(2).strip(), False
    elif start_flag in content:
        return content.replace(start_flag, "").strip(), "", True
    elif end_flag in content:
        parts = content.split(end_flag)
        return parts[0].strip(), parts[1].strip(), False
    return "", content, None


def simple_split_reasoning_text(content: str, start_flag: str = "<think>", end_flag: str = "</think>"):
    if start_flag in content:
        return True
    if end_flag in content:
        return False
    return None


async def process_updates_chunk(
        chunk: dict[str, Any],
        consumer_queue: asyncio.Queue,
        only_process_interrupt: bool = False
):
    data = chunk['data']

    if not only_process_interrupt:
        if 'model' in data:
            last_message: "AIMessage" = data['model']['messages'][-1]

            for block in last_message.content_blocks:
                block_type = block.get("type")

                if block_type == 'text':
                    think_start_flag = REASONING_FLAGS['deepseek'][0]
                    think_end_flag = REASONING_FLAGS['deepseek'][1]

                    res, txt, _ = split_reasoning_text(block.get('text', ''), think_start_flag, think_end_flag)
                    if res:
                        await consumer_queue.put({"type": "reasoning", "content": res})
                    if txt:
                        await consumer_queue.put({"type": "text", "content": txt})

                elif block_type in ('reasoning', 'thought', 'think'):
                    await consumer_queue.put({
                        "type": "reasoning",
                        "content": block.get('reasoning', '')
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

    if "__interrupt__" in data:
        interrupt_value = data['__interrupt__'][0].value
        action_requests = interrupt_value['action_requests']
        review_configs = interrupt_value['review_configs']

        assert len(action_requests) == len(review_configs)

        for action_request, review_config in zip(action_requests, review_configs):
            await consumer_queue.put({
                'type': 'interrupt',
                'content': {
                    'description': action_request['description'].split('\n\n')[0],
                    'name': action_request['name'],
                    'args': action_request['args'],
                    'allowed_decisions': review_config['allowed_decisions'],
                }
            })


async def process_messages_chunk(
        chunk: dict[str, Any],
        consumer_queue: asyncio.Queue,
        tool_buffers: dict,
        continue_as_reasoning: bool = False
):
    token: AIMessageChunk | ToolMessage = chunk['data'][0]

    if isinstance(token, ToolMessage):
        content = token.content if isinstance(token.content, str) else str(token.content)
        await consumer_queue.put({
            "type": "tool_result",
            "content": content
        })
        return continue_as_reasoning

    for block in token.content_blocks:
        block_type = block.get("type")

        if block_type == 'text':
            content = block.get('text', '')
            if bool(re.fullmatch(r"\n+", content)):
                continue

            think_start_flag = REASONING_FLAGS['deepseek'][0]
            think_end_flag = REASONING_FLAGS['deepseek'][1]

            res, txt, new_state = split_reasoning_text(content, think_start_flag, think_end_flag)

            if new_state is not None:
                continue_as_reasoning = new_state

            if continue_as_reasoning:
                val = res or txt
                if val:
                    await consumer_queue.put({"type": "reasoning", "content": val})
            else:
                if res:
                    await consumer_queue.put({"type": "reasoning", "content": res})
                if txt:
                    await consumer_queue.put({"type": "text", "content": txt})

        elif block_type == 'reasoning':
            await consumer_queue.put({
                "type": "reasoning",
                "content": block.get('reasoning', '')
            })

        elif block_type == 'tool_call_chunk':
            # case 1: same type or first ever block → keep accumulating
            idx = block.get("index")
            if idx not in tool_buffers:
                tool_buffers[idx] = {"id": "", "name": "", "args": "", "index": idx}

            # update tool call chunk into buffer
            for field in ['id', 'name', 'index', 'args']:
                if block.get(field):
                    if field == 'args':
                        tool_buffers[idx][field] += block[field]
                    else:
                        tool_buffers[idx][field] = block[field]

    if not getattr(token, 'tool_call_chunks'):
        await process_tool_buffers(consumer_queue, tool_buffers)

    return continue_as_reasoning


async def process_tool_buffers(progression_queue: asyncio.Queue, tool_buffers: dict):
    """Combine tool buffer to a tool call then out to queue."""
    if not tool_buffers:
        return

    for idx, tool in tool_buffers.items():
        try:
            clean_args = json.loads(tool["args"]) if tool["args"] else {}
        except json.JSONDecodeError:
            clean_args = tool["args"]

        tool_content = {
            "id": tool["id"],
            "name": tool["name"],
            "args": clean_args
        }
        formatted_tool = {
            "type": "tool_call",
            "content": tool_content
        }

        await progression_queue.put(formatted_tool)

    tool_buffers.clear()
