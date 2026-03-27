#
#  Copyright (c) 2026
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from typing import Literal
from mcp.server import FastMCP

TRANSPORT = Literal["stdio", "sse", "streamable-http"]


class AccessibleFastMCP(FastMCP):
    _transport: TRANSPORT

    def __init__(
        self,
        *args,
        host: str = "127.0.0.1",
        port: int = 8000,
        mount_path: str = "/",
        sse_path: str = "/sse",
        message_path: str = "/messages/",
        streamable_http_path: str = "/mcp",
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self._host = host
        self._port = port
        self._mount_path = mount_path
        self._sse_path = sse_path
        self._message_path = message_path
        self._streamable_http_path = streamable_http_path

    @property
    def host(self):
        return self._host

    @property
    def port(self):
        return self._port

    @property
    def mount_path(self):
        return self._mount_path

    @property
    def sse_path(self):
        return self._sse_path

    @property
    def message_path(self):
        return self._message_path

    @property
    def streamable_http_path(self):
        return self._streamable_http_path

    @property
    def endpoint_url(self):
        return f"{self.host}/{self.port}/{self.sse_path.strip('/')}"

    def run(
        self,
        transport: Literal["stdio", "sse", "streamable-http"] = "sse",
        mount_path: str | None = None,
    ) -> None:
        self._transport = transport
        super().run('sse')

    def __getstate__(self):
        return {
            'sever_name': self.name,
            'endpoint_url': self.endpoint_url
        }

