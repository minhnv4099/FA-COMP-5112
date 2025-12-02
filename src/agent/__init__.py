#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations

from typing import TYPE_CHECKING

from src._import_utils import import_attr

if TYPE_CHECKING:
    from src.agent.base import BaseAgent
    from src.agent.react_loop import LoopReactAgent, ReactStatefulAgent

    from src.agent.planner import PlannerAgent
    from src.agent.retriever import RetrieverAgent
    from src.agent.coding import CodingAgent
    from src.agent.critic import CriticAgent
    from src.agent.verification import VerificationAgent
    from src.agent.user import UserAgent

__all__ = (
    "BaseAgent",
    "LoopReactAgent",
    "ReactStatefulAgent",
    # COMP 5112 agents
    "PlannerAgent",
    "RetrieverAgent",
    "CodingAgent",
    "CriticAgent",
    "VerificationAgent",
    "UserAgent"
)

__dynamic_imports = {
    "BaseAgent": "base",
    "LoopReactAgent": "react_loop",
    "ReactStatefulAgent": "react_loop",
    "PlannerAgent": "planner",
    "RetrieverAgent": "retriever",
    "CodingAgent": "coding",
    "CriticAgent": "critic",
    "VerificationAgent": "verification",
    "UserAgent": "user"
}


def __getattr__(attr_name: str) -> object:
    module_name = __dynamic_imports.get(attr_name)
    result = import_attr(attr_name, module_name, package=__spec__.parent)
    globals()[attr_name] = result
    return result


def __dir__() -> list[str]:
    return list(__all__)
