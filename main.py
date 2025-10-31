#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import hydra
from omegaconf import DictConfig

from src.base.coordinator import Coordinator
from dotenv import load_dotenv

ENV_FILES = [
    'secret.env',
    '.env',
]
for file in ENV_FILES:
    try:
        is_load_env = load_dotenv(dotenv_path=file)
    except FileNotFoundError as e:
        pass


@hydra.main(config_path="configs", config_name="job", version_base=None)
def main(cfg: DictConfig):
    planner_agent = Coordinator.build_agent(agent_config=cfg.agent.planner)
    retriever_agent = Coordinator.build_agent(agent_config=cfg.agent.retriever)
    coding_agent = Coordinator.build_agent(agent_config=cfg.agent.coding)
    critic_agent = Coordinator.build_agent(agent_config=cfg.agent.critic)
    verification_agent = Coordinator.build_agent(agent_config=cfg.agent.verification)
    user_proxy_agent = Coordinator.build_agent(agent_config=cfg.agent.user)

    graph = Coordinator.build_graph(
        nodes=(
            planner_agent, retriever_agent, coding_agent,
            critic_agent, verification_agent, user_proxy_agent),
        **cfg.graph
    )
    graph.init_graph()
    graph.invoke(cfg.task)


if __name__ == '__main__':
    main()
