#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from src.utils import scan_module

from src.agent.base import BaseAgent
from src.agent.react_loop import LoopReactAgent, ReactStatefulAgent

from src.agent.planner import PlannerAgent
from src.agent.retriever import RetrieverAgent
from src.agent.coding import CodingAgent
from src.agent.critic import CriticAgent
from src.agent.verification import VerificationAgent
from src.agent.user import UserAgent

__module_lookup = {
    "base": "BaseAgent",
    "react": "LoopReactAgent",
    "stateful_react": "ReactStatefulAgent",
    "planner": "PlannerAgent",
    "retriever": "RetrieverAgent",
    "coding": "CodingAgent",
    "critic": "CriticAgent",
    "verification": "VerificationAgent",
    "user": "UserAgent"
}


def __getattr__(name):
    return __module_lookup[name]


__all__ = scan_module(globals())
