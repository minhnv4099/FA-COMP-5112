#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations

import logging
import importlib
from collections import defaultdict
from typing import Union, TYPE_CHECKING, Optional

from src.types import ClassLike, SchemaLike, MappingLike
from src.utils.exception import NotFoundSchema, NotFoundTool

if TYPE_CHECKING:
    from src.tool.base import BaseDefinedTool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REGISTRY = defaultdict(dict)
"""Registry used to to register class"""

FUNCTION_REGISTRY = defaultdict(dict)
"""Registry used to to register function"""


def load_class(type: str, name: str) -> Union[ClassLike, callable]:
    _type = type.lower()
    _name = name.lower()

    if _type not in REGISTRY:
        raise KeyError(f"'{_type}' not found. Available types: {list(REGISTRY.keys())}")

    type_bucket = REGISTRY[_type]

    if _name not in type_bucket:
        raise KeyError(f"'{_name}' not found in '{_type}'. Available names: {list(type_bucket.keys())}")

    info = type_bucket[_name]

    module = importlib.import_module(name=info['path'])
    cls = getattr(module, info['symbol_name'])

    return cls


def load_tool(name: str, **kwargs) -> BaseDefinedTool:
    try:
        return load_class(type='tool', name=name)(**kwargs)
    except KeyError as e:
        raise NotFoundTool


def fetch_registered(metadata: Optional[MappingLike]) -> Union[None, SchemaLike]:
    if metadata is None:
        return None

    if not isinstance(metadata, MappingLike):
        raise ValueError(f"metadata must be like-dict, but got {type(metadata)!r}")

    try:
        if metadata['type'] == 'tool':
            return load_tool(name=metadata['name'], **metadata.get('tool_kwargs', dict()))

        return load_class(type=metadata['type'], name=metadata['name'])

    except KeyError as e:
        raise NotFoundSchema(e.args)


class Register:
    """The Register Class used to register a class to a type of class (e.g., agent, model, state, schema) \n
    Using this technique helps with no need of manual import modules and packages.

    When using function ``load_class`` Python will find a module path based on ``type`` and ``name`` and import
    them, then return class what had been registered.

    Args:
        type (str):
            Type of class (node, state, agent, chat, ...). MUST be lowercase
        module_path (str):
            Path to module containing this class. MUST be lowercase
        name (str):
            Unique name of class in ``type`` list. MUST be lowercase
    """

    def __init__(
        self,
        type: str,
        module_path: str,
        name: Union[str, list[str]]
    ):
        self.module_path = module_path.lower()
        self.type = type.lower()
        self.name = name.lower()

    def __call__(self, symbol: ClassLike) -> ClassLike:
        name_to_class = REGISTRY[self.type]

        if self.name in name_to_class:
            raise ValueError(
                f"'{self.name}' exists. Existing names in type '{self.type}': {', '.join([f'{_name}' for _name in name_to_class])}")
        else:
            # logger.info(f"'{symbol.__name__}' has registered as '{self.type}' with path: '{symbol.__module__}'")
            ...

        name_to_class[self.name] = {
            'symbol_name': symbol.__name__,
            'path': self.module_path,
            'symbol': symbol
        }

        return symbol


class _Register(Register):
    """The Register class used to register a particular class identified by ``type``

    ``type`` = <TYPE>
    """

    type: str

    def __init__(self, module_path: str, name: str):
        super().__init__(type=self.type, module_path=module_path, name=name)


class RegisterState(_Register):
    """The Register class used to register state class

    ``type`` = 'state'
    """

    type: str = 'state'


class RegisterChat(_Register):
    """The Register class used to register chat class

    ``type`` = 'chat'
    """

    type: str = 'chat'


class RegisterAgent(_Register):
    """The Register class used to register agent class

    ``type`` = 'agent'
    """

    type: str = 'agent'


class RegisterNode(_Register):
    """The Register class used to register node class

    ``type`` = 'node'
    """

    type: str = 'node'


class RegisterSchema(_Register):
    """The Register class used to register schema class

    ``type`` = 'schema'
    """

    type: str = 'schema'


class RegisterChatOutputSchema(_Register):
    """The Register class used to register chat output class

    ``type`` = 'chat_output'
    """

    type = 'chat_output'


class RegisterGraph(_Register):
    """The Register class used to register graph class

    ``type`` = 'graph'
    """

    type = 'graph'


class RegisterToolSchema(RegisterSchema):
    """The Register class used to register tool shema class

    ``type`` = 'tool_schema'
    """

    type = 'tool_schema'


class RegisterTool(_Register):
    """The Register class used to register tool shema class

    ``type`` = 'tool'
    """

    type = 'tool'
