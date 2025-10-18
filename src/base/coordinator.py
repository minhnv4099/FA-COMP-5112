#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#

from .graph import BaseGraph
from .mapping import get_class


class Coordinator:
    """The Coordinator class"""

    def __init__(self, process_config):
        self.config = process_config

    @classmethod
    def build_agent(cls, agent_config):
        agent_cls = get_class(type='agent', name=agent_config.name)
        return agent_cls(**agent_config)

    @classmethod
    def build_graph(cls, nodes, state_schema):
        return BaseGraph(name='The entire graph', nodes=nodes, state_schema=state_schema)
