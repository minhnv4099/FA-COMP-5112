#
#  Copyright (c) 2026
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations

import json
import re
from collections import OrderedDict
from typing import TYPE_CHECKING

from langchain.tools import BaseTool

if TYPE_CHECKING:
    from langchain.agents.middleware import AgentMiddleware

DECISION_TOOLS = OrderedDict({
    'write_todos': False,
    'execute': {"allowed_decisions": ["approve", "edit", "reject"]},
    'write': {"allowed_decisions": ["approve", "edit", "reject"]},
    'append': {"allowed_decisions": ["approve", "edit", "reject"]},
    'run': {"allowed_decisions": ["approve", "edit", "reject"]},
    'shell': {"allowed_decisions": ["approve", "edit", "reject"]},
    'read': {"allowed_decisions": ["approve", "reject"]},
    'lists': False,
    'others': False
})


def auto_validate_interrupt_tools(tools: list[str | BaseTool]):
    """Auto infer allowed decisions based tool name"""
    interrupt_on = {}
    for tool in tools:

        if isinstance(tool, BaseTool):
            tool, allowed_decisions = auto_resolve_allowed_decisions(tool)
            tool_name = tool.name
        else:
            tool_name = tool
            allowed_decisions = None

        if allowed_decisions is not None:
            interrupt_on[tool_name] = allowed_decisions
            continue

        for t in DECISION_TOOLS.keys():
            if t in tool_name:
                interrupt_on[tool_name] = DECISION_TOOLS[t]
                break
        else:
            interrupt_on[tool_name] = DECISION_TOOLS['others']

    return interrupt_on


def auto_resolve_allowed_decisions(tool: BaseTool):
    docstring = tool.description

    if not docstring:
        return None, None

    # Pattern tìm kiếm: {"allowed_decisions": [...]}
    # Sử dụng re.DOTALL để khớp cả xuống dòng nếu JSON dài
    pattern = r'\{"allowed_decisions":\s*.*\s*\}'
    match = re.search(pattern, docstring, re.DOTALL)

    allowed_decisions: dict | bool | None = None
    clean_doc = docstring

    if match:
        try:
            json_str = match.group(0)
            data = json.loads(json_str)
            allowed_decisions_info = data.get('allowed_decisions', False)
            if isinstance(allowed_decisions_info, bool):
                allowed_decisions = allowed_decisions_info
            else:
                allowed_decisions = data

            # remove decision info from tool docstring
            clean_doc = docstring.replace(json_str, "").strip()
        except json.JSONDecodeError:
            pass

    tool.description = clean_doc

    return tool, allowed_decisions


def get_middleware_tools(middlewares: list['AgentMiddleware']):
    """Get tools of middlewares."""
    middleware_tools: list[BaseTool] = []
    for middleware in middlewares:
        middleware_tools.extend(getattr(middleware, 'tools', []))

    return middleware_tools
