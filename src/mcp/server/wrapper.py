#
#  Copyright (c) 2026
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import json
from typing import Literal, Any, Callable
from mcp.server import FastMCP
from mcp.types import ToolAnnotations, Icon, AnyFunction

TRANSPORT = Literal["stdio", "sse", "streamable-http"]


class AccessibleFastMCP(FastMCP):
    _transport: TRANSPORT

    def __init__(
        self,
        *args,
        name: str | None = None,
        instructions: str | None = None,
        host: str = "127.0.0.1",
        port: int = 8000,
        mount_path: str = "/",
        sse_path: str = "/sse",
        message_path: str = "/messages/",
        streamable_http_path: str = "/mcp",
        **kwargs
    ):
        super().__init__(
            *args,
            name=name,
            instructions=instructions,
            host=host,
            port=port,
            mount_path=mount_path,
            sse_path=sse_path,
            message_path=message_path,
            streamable_http_path=streamable_http_path,
            **kwargs
        )

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

    @property
    def meta(self):
        return {
            'name': self.name,
            'host': self._host,
            'port': self._port,
            'instructions': self.instructions,
            'endpoint_url': self.endpoint_url
        }

    def tool(
        self,
        name: str | None = None,
        title: str | None = None,
        description: str | None = None,
        annotations: ToolAnnotations | None = None,
        icons: list[Icon] | None = None,
        meta: dict[str, Any] | None = None,
        structured_output: bool | None = None,
        human_confirm: bool | list[Literal['approve', 'edit', 'reject']] = False,
    ) -> Callable[[AnyFunction], AnyFunction]:
        """Override tool method that can provide allow decisions for human
        in loop interruption."""
        if callable(name):
            raise TypeError(
                "The @tool decorator was used incorrectly. Did you forget to call it? Use @tool() instead of @tool"
            )

        allowed_decisions = ['approve', 'edit', 'reject']
        if isinstance(human_confirm, bool):
            allowed_decisions = human_confirm
        else:
            allowed_decisions = list(sorted(set(allowed_decisions).intersection(set(human_confirm)), reverse=False))
            if not allowed_decisions:
                allowed_decisions = False

        allowed_decisions = {"allowed_decisions": allowed_decisions}

        def decorator(fn: AnyFunction) -> AnyFunction:
            _description = description or fn.__doc__
            _description = _description + json.dumps(allowed_decisions)

            self.add_tool(
                fn,
                name=name,
                title=title,
                description=_description,
                annotations=annotations,
                icons=icons,
                meta=meta,
                structured_output=structured_output,
            )
            return fn

        return decorator
