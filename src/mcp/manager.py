#
#  Copyright (c) 2026
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations

from typing import TYPE_CHECKING
from contextlib import contextmanager
from logging import getLogger

from langchain_mcp_adapters.client import MultiServerMCPClient

if TYPE_CHECKING:
    from src.mcp.server.wrapper import AccessibleFastMCP

MCP_SERVER_MONITOR: dict[str, AccessibleFastMCP] = dict()
logger = getLogger('MCPServer Manager')


@contextmanager
def run_mcp_server(mcp_server: AccessibleFastMCP):
    try:
        logger.info(f'MCP Server {mcp_server.name!r} is running')
        logger.info(f"Added MCP server {mcp_server.name!r} into manager.")
        MCP_SERVER_MONITOR[mcp_server.name] = mcp_server
        yield
    except KeyboardInterrupt:
        pass
    finally:
        logger.info(f'MCP Server {mcp_server.name!r} stopped')
        MCP_SERVER_MONITOR.pop(mcp_server.name, None)
        logger.info(f'Removed MCP server {mcp_server.name!r} from manager.')


def list_active_mcp_servers():
    return MCP_SERVER_MONITOR


def auto_create_mcp_client():
    connection_params = dict()
    for name, mcp_server in MCP_SERVER_MONITOR.items():
        if mcp_server:
            connection_params.setdefault(name, mcp_server.tool)

    if connection_params:
        return MultiServerMCPClient(connection_params)

    return None
