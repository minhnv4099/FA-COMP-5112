#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import logging

from .graph import BaseGraph
from .mapping import get_class

logger = logging.getLogger(__name__)


class Coordinator:
    """The Coordinator class"""

    def __init__(self, process_config):
        self.config = process_config

    @classmethod
    def build_agent(cls, agent_config):
        logger.info(f"Build {agent_config.name} Agent: {agent_config.model_name}")
        agent_cls = get_class(type='agent', name=agent_config.name)
        return agent_cls(**agent_config)

    @classmethod
    def build_graph(cls, nodes, **graph_config):
        logger.info(f"Build a graph")
        return BaseGraph(name='The entire graph', nodes=nodes, **graph_config)
