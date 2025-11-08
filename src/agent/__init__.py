#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from src.agent.coding import CodingAgent
from src.agent.critic import CriticAgent
from src.agent.planner import PlannerAgent
from src.agent.retriever import RetrieverAgent
from src.agent.user import UserAgent
from src.agent.verification import VerificationAgent

__module_lookup = {
    "planner": "PlannerAgent",
    "retriever": "RetrieverAgent",
    "coding": "CodingAgent",
    "critic": "CriticAgent",
    "verification": "VerificationAgent",
    "user": "UserAgent",
}


def __getattr__(name):
    return __module_lookup[name]


__all__ = list(__module_lookup.values())
