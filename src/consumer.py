#
#  Copyright (c) 2026
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import sys
import json
import random
import asyncio
from asyncio import Queue
from typing import TypedDict, Union


class Block(TypedDict):
    type: str
    content: Union[str, dict]


async def streaming_print(_queue: Queue[Block]):
    """Print element in queue until the end."""
    current_type = None

    while True:
        data = await _queue.get()
        if data is None:
            sys.stdout.write('\n')
            sys.stdout.flush()
            break

        msg_type = data['type']
        content = data['content']

        if msg_type != current_type:
            header = f"\n------ {msg_type.upper()} ------\n"
            sys.stdout.write(header)
            current_type = msg_type

        if msg_type == 'tool_call' or msg_type == 'interrupt':
            output = json.dumps(content, indent=2) + "\n"
        elif msg_type == 'tool_result':
            output = content
            if len(content) > 500:
                output = content[:500] + '\n...'
        else:
            output = content

        for char in output:
            sys.stdout.write(char)
            sys.stdout.flush()
            await asyncio.sleep(random.uniform(0.0003, 0.002))

        _queue.task_done()


async def streaming_yield(_queue: Queue):
    """Yield elements in queue until streaming stops
    It likes do nothing.
    """
    while True:
        data = await _queue.get()
        if data is None:
            break

        if data is None:
            _queue.task_done()
            break

        # yield the original data
        yield data

        _queue.task_done()
