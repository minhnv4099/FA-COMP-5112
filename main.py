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
    model_name = "amazon/nova-2-lite-v1:free"
    llm_engine = Builder.build(type='llm', model_name=model_name)
    mcp_client = MultiServerMCPClient(
        server_script_path=[
            ("blender", "blender_mcp_entrypoint.py"),
            ("gmail", "src/mcp/server/gmail_api.py"),
            ("filesystem", "src/mcp/server/file.py"),
            ("weather", "src/mcp/server/weather.py"),]
    )

    chat = Builder.build(
        type='agent',
        interface='react_agent',
        llm_engine=llm_engine,
        mcp_client=mcp_client,
        schemas=[
            {'type': 'tool', 'name': 'url_reader'},
            {'type': 'chat_output', 'name': 'base'},
        ]
    )

    response = chat.invoke('Summarize the latest mesage I sent')
    response.pretty_print()
    # response = chat.invoke('Summarize what is my name')
    # response.pretty_print()
    chat.print_conversation()


if __name__ == '__main__':
    main()
