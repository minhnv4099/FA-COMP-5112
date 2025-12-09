#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import logging

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s][%(levelname)s][%(name)s][%(funcName)s] - %(message)s #%(lineno)d'
)

from src.builder import Builder
from src.utils import find_load_env
from src.mcp.client import MultiServerMCPClient, SingleServerMCPClient

find_load_env()

logger = logging.getLogger(__name__)


def main():
    mcp_client = MultiServerMCPClient(
        server_script_path=[
            ("gmail", "src/mcp_server_entrypoint/gmail.py"),
            ("filesystem", "src/mcp_server_entrypoint/filesystem.py"),
            ("weather", "src/mcp_server_entrypoint/weather.py"),
            # ("blender", "src/mcp_server_entrypoint/blender.py"),
        ]
    )

    model_name = "amazon/nova-2-lite-v1:free"
    llm_engine = Builder.build(type='llm', model_name=model_name)
    schemas = [
        {'type': 'tool', 'name': 'url_reader'},
        {'type': 'chat_output', 'name': 'base'},
    ]

    chat = Builder.build(
        type='agent',
        interface='react_stateful_agent',
        llm_engine=llm_engine,
        mcp_client=mcp_client,
    )

    while True:
        message = input("Enter message: ").strip()
        if message == 'q':
            break
        response = chat.invoke(message)
        response.pretty_print()

    chat.print_conversation()


if __name__ == '__main__':
    main()
