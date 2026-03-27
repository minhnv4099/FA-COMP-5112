#
#  Copyright (c) 2026
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from langchain_core.messages import HumanMessage
from typing import Type, TypeVar, Callable, Optional, cast
import functools
import inspect

T = TypeVar("T")


def auto_validate_input(old_func: Callable):
    """Wrap a method to give it an ability to validate convert input (any valid type)
    to `obj`:'HumanMessage' which is consistent input for `obj`:'BaseChatModel'.

    That is useful when passing message into chat a dict, str or any type that can be
    constructed `obj`:'HumanMessage'.

    Args:
        old_func (Callable): Function or method.
    """
    @functools.wraps(old_func)
    def decorator(obj: Type[T], *args, **kwargs):
        inspect.getfullargspec(old_func)

        if not args:
            raise ValueError("No get positional required `input`.")

        _input = args[0]

        if isinstance(_input, str):
            _input = {"messages": [HumanMessage(content=_input)]}

        args = (_input, ) + args[1:]

        return old_func(obj, *args, **kwargs)

    return decorator


def return_last_message(old_func: Callable[[...], dict]):
    @functools.wraps(old_func)
    def decorator(*args, **kwargs):
        state = old_func(*args, **kwargs)

        messages = state['messages']
        if messages:
            return messages[-1]
        return None

    return decorator


def cast_to_type(_type: Optional[Type[T]] = None):
    def wrapper(old_func: Callable):
        @functools.wraps(old_func)
        def decorator(*args, **kwargs):
            output = old_func(*args, **kwargs)
            if _type is None:
                return output

            try:
                return _type(**output.__dict__)
            except:
                return output

        return decorator
    return wrapper
