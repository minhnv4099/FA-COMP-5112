#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import hydra
import logging
from omegaconf import DictConfig

from src.builder import Builder
from src.utils import find_load_env

find_load_env()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@hydra.main(config_path="configs", config_name="job", version_base=None)
def main(cfg: DictConfig):
    planner_agent = Builder.build_agent(agent_config=cfg.agent.planner)
    retriever_agent = Builder.build_agent(agent_config=cfg.agent.retriever)
    # coding_agent = Builder.build_agent(agent_config=cfg.agent.coding)
    # critic_agent = Builder.build_agent(agent_config=cfg.agent.critic)
    # verification_agent = Builder.build_agent(agent_config=cfg.agent.verification)
    # user_proxy_agent = Builder.build_agent(agent_config=cfg.agent.user)
    #
    # graph = Builder.build_graph(
    #     nodes=(
    #         planner_agent, retriever_agent, coding_agent,
    #         critic_agent, verification_agent, user_proxy_agent),
    #     graph_config=cfg.graph
    # )

    graph = Builder.build_graph(
        nodes=[
            planner_agent,
            retriever_agent
        ],
        graph_config=cfg.graph
    )

    graph.init_graph()

    graph.invoke('Hi')

    graph.invoke("Execute file configs/agents/critic.yaml")

    graph.print_conversation()


if __name__ == '__main__':
    main()
