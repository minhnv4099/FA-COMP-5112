#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import logging

from src.builder import Builder
from src.utils import find_load_env
from src.chat import BaseChat, StatefulChat, ToolCallGenerateChat

find_load_env()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    llm = Builder.build(type='llm')
    chat = StatefulChat(llm_engine=llm)

    response = chat.invoke(input="hello my name is Minh. Who are you?")
    response = chat.invoke(input='What my name?')

    chat.print_conversation()


if __name__ == '__main__':
    main()
