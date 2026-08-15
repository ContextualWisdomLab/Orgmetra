"""Cover non-request ASGI messages at the request boundary."""

from __future__ import annotations

import asyncio
from uuid import UUID

from starlette.types import Message, Receive, Scope, Send

from orgmetra_people_api.middleware import RequestBoundaryMiddleware


def test_http_disconnect_message_passes_without_body_accounting() -> None:
    """Pass disconnect messages through and still secure the response."""

    trace_reference = UUID("0198a412-6000-7000-8000-000000000005")
    sent: list[Message] = []

    async def app(_scope: Scope, receive: Receive, send: Send) -> None:
        message = await receive()
        assert message["type"] == "http.disconnect"
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    async def receive() -> Message:
        return {"type": "http.disconnect"}

    async def send(message: Message) -> None:
        sent.append(message)

    scope: Scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "https",
        "path": "/disconnect",
        "raw_path": b"/disconnect",
        "query_string": b"",
        "root_path": "",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 443),
        "state": {},
    }
    middleware = RequestBoundaryMiddleware(
        app,
        maximum_body_bytes=1,
        identifier_factory=lambda: trace_reference,
    )

    asyncio.run(middleware(scope, receive, send))

    assert sent[0]["status"] == 204
    assert (b"x-request-id", str(trace_reference).encode("ascii")) in sent[0][
        "headers"
    ]
