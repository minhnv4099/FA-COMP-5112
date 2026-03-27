#
#  Copyright (c) 2026
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import sys
import json
import random
import asyncio
from asyncio import Queue


async def streaming_print(_queue: Queue):
    current_mode = None

    while True:
        data = await _queue.get()
        if data is None:
            sys.stdout.write('\n')
            sys.stdout.flush()
            break

        msg_type = data['type']
        content = data['content']

        # In Header nếu đổi loại block (giúp nhìn đẹp trên terminal)
        if msg_type != current_mode:
            header = f"\n------ {msg_type.upper()} ------\n"
            sys.stdout.write(header)
            current_mode = msg_type

        # Xử lý nội dung
        if msg_type == 'tool_call':
            # Nếu là tool call chunk, format json cho đẹp
            output = json.dumps(content, indent=2) + "\n"
        else:
            output = content

        if msg_type == 'tool_result':
            if len(content) > 500:
                content = content[:500] + '\n...'

            output = content

        for char in output:
            sys.stdout.write(char)
            sys.stdout.flush()
            await asyncio.sleep(random.uniform(0.003, 0.02))


async def streaming_yield(_queue: Queue):
    """Yield elements in queue until streaming stops
    It likes do nothing.
    """
    while True:
        data = await _queue.get()
        if data is None:
            break

        yield data
