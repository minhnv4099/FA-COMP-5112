#
#  Copyright (c) 2026
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations
from typing import Any, TYPE_CHECKING
from langchain.agents.middleware import (
    HumanInTheLoopMiddleware, InterruptOnConfig)
from langchain.agents.middleware import PIIMiddleware
from langchain.agents.middleware import TodoListMiddleware
from langchain.agents.middleware import SummarizationMiddleware
from langchain.agents.middleware import (
    ShellToolMiddleware, HostExecutionPolicy, DockerExecutionPolicy
)

if TYPE_CHECKING:
    from langchain.agents.middleware import AgentMiddleware


def create_human_in_loop_middleware(interrupt_on: dict[str, bool | InterruptOnConfig]):
    return [
        HumanInTheLoopMiddleware(
            interrupt_on=interrupt_on,
            description_prefix="Tool execution pending approval",
        )
    ]


def create_pii_middleware():
    return [
        # PIIMiddleware("email", strategy="redact"),
        PIIMiddleware("credit_card", strategy="mask"),
        PIIMiddleware("url", strategy="redact"),
        PIIMiddleware("ip", strategy="hash"),
        PIIMiddleware("api_key", detector=r"sk-[a-zA-Z0-9]{32}", strategy="block")
    ]


def create_todo_middleware():
    return [
        TodoListMiddleware()
    ]


def create_shell_middleware():
    return [
        ShellToolMiddleware(
            execution_policy=HostExecutionPolicy()
        )
    ]


def create_summarize_middleware(
        model: str = 'openrouter:nvidia/nemotron-3-super-120b-a12b:free',
        base_url: str = None,
        api_key: str = None
):
    from langchain.chat_models import init_chat_model
    model = init_chat_model(
        model=model,
        base_url=base_url,
        api_key=api_key,
    )
    return [
        SummarizationMiddleware(model=model)
    ]


def create_default_middlewares():
    """Create default middlewares except of `HumanInTheLoopMiddleware`
    Because we need to resolve interrupt on.
    """
    middlewares: list['AgentMiddleware'] = []

    middlewares.extend(create_pii_middleware())
    middlewares.extend(create_todo_middleware())
    middlewares.extend(create_summarize_middleware())
    middlewares.extend(create_shell_middleware())

    return middlewares
