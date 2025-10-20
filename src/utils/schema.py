#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from src.base.mapping import get_class


def fetch_schema(schema):
    try:
        return get_class(type=schema['type'], name=schema['name'])
    except KeyError:
        return schema
