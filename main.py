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
from src.mcp.client import MCPClientToolExecutor

find_load_env()

logger = logging.getLogger(__name__)


def main():
    llm_engine = Builder.build(type='llm', model_name="openai/gpt-5-nano")
    mcp_client = MCPClientToolExecutor(server_script_path="src/mcp/server/file.py")

    chat = Builder.build(
        type='agent',
        interface='react_stateful_agent',
        llm_engine=llm_engine,
        mcp_client=mcp_client,
        tool_schemas=[
            {
                "type": "tool",
                "name": "url_reader"
            }
        ])

    response = chat.invoke('Hello, My name is Minh. what file .env says')
    response.pretty_print()
    response = chat.invoke('Summarize what is my name')
    response.pretty_print()


if __name__ == '__main__':
    main()
