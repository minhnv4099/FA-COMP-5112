#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Union, Literal
from typing_extensions import TypedDict, TypeAlias
from collections import defaultdict
from src.graph.base import BaseGraph
from src.registry import load_class

if TYPE_CHECKING:
    from src.chat import BaseChat, StatefulChat, ToolCallGenerateChat
    from src.agent.base import BaseAgent
    from src.node.base import BaseNode

logger = logging.getLogger(__name__)

Available_LLM_interfaces: TypeAlias = Literal[
    'base_chat',
    'tool_call_generate_chat',
    'tool_call_execute_chat',
    'stateful_chat',
    'tool_call_execute_stateful_chat',
    'tool_call_generate_stateful_chat',
    'base_agent',
    'react_agent',
    'react_stateful_agent',
    # comp 5112
    'planner',
    'retriever',
    'coding',
    'critic',
    'verification',
    'user'
]


class Builder:
    """The Coordinator class"""

    def __init__(self, process_config):
        self.config = process_config

    @classmethod
    def build(
        cls,
        type: Literal['chat', 'agent', 'graph', 'llm'],
        name: Available_LLM_interfaces = None,
        **kwargs
    ):
        """No need to define name in ``config``. Pass by ``name``"""
        if type == 'llm':
            type = 'chat'
            name = 'base_chat'

        config = kwargs if kwargs else defaultdict(lambda: None)
        config['name'] = name if name else ...

        if type == 'chat':
            return cls.build_chat(config)
        elif type == 'agent':
            return cls.build_agent(config)
        else:
            return cls.build_graph(graph_config=config, nodes=kwargs.get('nodes', []))

    @classmethod
    def build_agent(
        cls,
        agent_config: dict,
    ) -> Union[BaseAgent]:
        """"""
        logger.info(f"Create '{agent_config['name']}' agent: {agent_config['model_name']}")
        agent_cls = load_class(type='agent', name=agent_config['name'])

        return agent_cls(**agent_config)

    @classmethod
    def build_chat(
        cls,
        chat_config: dict
    ) -> BaseChat | StatefulChat:
        logger.info(f"Create '{chat_config['name']}' chat: {chat_config['model_name']}")
        chat_cls = load_class(type='chat', name=chat_config['name'])

        return chat_cls(**chat_config)

    @classmethod
    def build_graph(
        cls,
        nodes: list[Union[BaseNode, BaseAgent]],
        graph_config
    ) -> BaseGraph:
        """"""
        logger.info(f"Build the graph")
        return BaseGraph(name='The entire graph', nodes=nodes, **graph_config)
