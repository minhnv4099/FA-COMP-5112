#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Union, Sequence

from .base.graph import BaseGraph
from .registry import load_class

if TYPE_CHECKING:
    from .base.agent import BaseAgent
    from .base.node import BaseNode

logger = logging.getLogger(__name__)


class Coordinator:
    """The Coordinator class"""

    def __init__(self, process_config):
        self.config = process_config

    @classmethod
    def build_agent(
            cls,
            agent_config
    ) -> Union[BaseAgent]:
        """"""
        logger.info(f"Create {agent_config.name} agent: {agent_config.model_name}")
        agent_cls = load_class(type='agent', name=agent_config.name)
        return agent_cls(**agent_config)

    @classmethod
    def build_graph(
            cls,
            nodes: Sequence[Union[BaseNode, BaseAgent]],
            **graph_config
    ) -> BaseGraph:
        """"""
        logger.info(f"Build the graph")
        return BaseGraph(name='The entire graph', nodes=nodes, **graph_config)
