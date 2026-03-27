#
#  Copyright (c) 2026
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from langchain_core.tools import BaseTool


INTERRUPT_TOOLS = (
    'execute',
    'write',
    'append',
    'run'
)

NON_INTERRUPT_TOOLS = (
    'read',
    'list'
)


def auto_validate_interrupt_tools(tools: list[str | BaseTool]):
    interrupt_before = []
    interrupt_after = []
    for tool in tools:
        if isinstance(tool, BaseTool):
            tool_name = tool.name
        else:
            tool_name = tool

        if any(t in tool_name for t in INTERRUPT_TOOLS):
            interrupt_before.append(tool)
            continue

        if any(t in tool_name for t in NON_INTERRUPT_TOOLS):
            interrupt_before.append(tool_name)
            continue

    return interrupt_before, interrupt_after
