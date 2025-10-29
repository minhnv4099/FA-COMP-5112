#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from .coding import CodingAgent
from .critic import CriticAgent
from .planner import PlannerAgent
from .retriever import RetrieverAgent
from .user import UserAgent
from .verification import VerificationAgent

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
