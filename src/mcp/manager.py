#
#  Copyright (c) 2026
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations

import json
from typing import TYPE_CHECKING
from contextlib import contextmanager
from logging import getLogger
from src.mcp.client import MultiServerMCPClient

if TYPE_CHECKING:
    from src.mcp.server.wrapper import AccessibleFastMCP

MCP_SERVER_MONITOR: dict = dict()
logger = getLogger('MCPServer Manager')
tracking_file = 'src/mcp/running_mcp_server.json'


def get_running_server(info_file: str | None = None):
    info_file = info_file or tracking_file
    try:
        with open(info_file, 'r') as f:
            server_tracker = json.load(f)
            if not server_tracker:
                server_tracker = []
    except json.JSONDecodeError:
        server_tracker = []

    return server_tracker


def set_running_server(server_tracker: list, info_file: str | None = None):
    info_file = info_file or tracking_file
    try:
        with open(info_file, 'w') as f:
            json.dump(server_tracker, f, indent=3)
    except Exception:
        pass


def add_mcp_server(mcp_server: AccessibleFastMCP):
    server_tracker = get_running_server()
    server_tracker.append(mcp_server.meta)
    set_running_server(server_tracker)


def remove_mcp_server(mcp_server: AccessibleFastMCP):
    server_tracker = get_running_server()
    index_to_remove = []
    for idx, item in enumerate(server_tracker):
        if item['name'] == mcp_server.name and item['port'] == mcp_server.port:
            index_to_remove.append(idx)

    for index in index_to_remove:
        server_tracker[index] = None

    server_tracker = [ttt for ttt in server_tracker if ttt]
    set_running_server(server_tracker)


@contextmanager
def run_mcp_server(mcp_server: AccessibleFastMCP):
    try:
        logger.info(f'MCP Server {mcp_server.name!r} is running')
        logger.info(f"Added MCP server {mcp_server.name!r} into manager.")
        add_mcp_server(mcp_server)
        yield
    except (KeyboardInterrupt, BaseException):
        pass
    finally:
        logger.info(f'MCP Server {mcp_server.name!r} stopped')
        logger.info(f'Removed MCP server {mcp_server.name!r} from manager.')
        remove_mcp_server(mcp_server)


def auto_create_mcp_client(info_file: str | None = None) -> MultiServerMCPClient | None:
    info_file = info_file or tracking_file
    running_servers: list[dict] = get_running_server(info_file)

    connect_params = []
    for server_info in running_servers:
        connect_param = (server_info.get('name'), server_info.get('port'))
        connect_params.append(connect_param)

    return MultiServerMCPClient(connect_params)
