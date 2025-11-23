#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import glob
from typing import Union, Literal

from langgraph.types import Command, Send

from src.utils.file import clean_text


class DirectionRouter:
    """This class acts as a direction router base on 'Command' or 'Send' mechanism"""

    @classmethod
    def jump(
        cls,
        updates: dict,
        jump_to: str,
        method: Literal['command', 'send'] = 'command'
    ) -> Union[Command, Send, None]:
        if method.lower() == 'command':
            return Command(update=updates, goto=jump_to)

        elif method.lower() == 'send':
            return Send(arg=updates, node=jump_to)

        return None


def find_load_env():
    from dotenv import load_dotenv

    files = glob.glob(r"*.env") + ['.env', ]
    files = list(set(files))
    index_env = files.index('.env')
    last_env = files[-1]
    files[-1] = files[index_env]
    files[index_env] = last_env

    for f in files:
        try:
            is_load_env = load_dotenv(dotenv_path=f)
            if is_load_env:
                print(f"Loaded environment variables in file '{f}'")
                return
        except FileNotFoundError as e:
            continue
    else:
        print('No any "*.env" file to load environment variables. Let create a file and export')


def scan_module(module: dict) -> list:
    import inspect

    return [
        name
        for name, obj in module.items()
        if inspect.isclass(obj) or inspect.isfunction(obj)
    ]
