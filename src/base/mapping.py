#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import logging

logger = logging.getLogger(__name__)

AGENT_MAPPING = dict()

STATE_MAPPING = dict()

CONTEXT_MAPPING = dict()

TOOL_MAPPING = dict()

STRUCTURED_OUTPUT_MAPPING = dict()

GRAPH_MAPPING = dict()

MAPPING = {
    'agent': AGENT_MAPPING,
    'state': STATE_MAPPING,
    'tool': TOOL_MAPPING,
    'structured_output': STRUCTURED_OUTPUT_MAPPING,
    'graph': GRAPH_MAPPING,
    'context': CONTEXT_MAPPING,
}


def register(name: str, type: str):
    def inner_func(cls):
        try:
            object_mapping = MAPPING[type.lower()]
            if name in object_mapping:
                logger.critical(f"'{name}' has been already in '{type} mapping' "
                                f"with class '{object_mapping[name].__class__}', "
                                f"overriding '{cls}'")
            object_mapping[name.lower()] = cls
        except KeyError as e:
            logger.error(f"Mapping doesn't have '{type}'")

        return cls

    return inner_func


def get_class(type: str, name: str):
    try:
        return MAPPING[type.lower()][name.lower()]
    except KeyError as e:
        return None


def fetch_schema(schema):
    if schema is None:
        return None
    try:
        return get_class(type=schema['type'], name=schema['name'])
    except KeyError:
        return None
