"""Direct ASGI tests for request size and response security boundaries."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

import pytest
from starlette.types import Message, Receive, Scope, Send

from orgmetra_people_api.middleware import RequestBoundaryMiddleware


TRACE_REFERENCE = UUID("0198a412-6000-7000-8000-000000000004")
SUPPORT_REFERENCE = UUID("0198a412-6000-7000-8000-000000000104")


def _http_scope(headers: list[tuple[bytes, bytes]] | None = None) -> Scope:
    """Return a complete minimal HTTP scope."""

    return {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "https",
        "path": "/bounded",
        "raw_path": b"/bounded",
        "query_string": b"",
        "root_path": "",
        "headers": headers or [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 443),
        "state": {},
    }


def _middleware(
    app: Callable[[Scope, Receive, Send], Awaitable[None]],
    maximum_body_bytes: int,
) -> RequestBoundaryMiddleware:
    """Create middleware with separate deterministic internal and client IDs."""

    return RequestBoundaryMiddleware(
        app,
        maximum_body_bytes=maximum_body_bytes,
        identifier_factory=lambda: TRACE_REFERENCE,
        support_identifier_factory=lambda: SUPPORT_REFERENCE,
    )


def _run(
    app: Callable[[Scope, Receive, Send], Awaitable[None]],
    scope: Scope,
    messages: list[Message],
) -> list[Message]:
    """Run one ASGI application and return sent messages."""

    async def scenario() -> list[Message]:
        queue = list(messages)
        sent: list[Message] = []

        async def receive() -> Message:
            return queue.pop(0)

        async def send(message: Message) -> None:
            sent.append(message)

        await app(scope, receive, send)
        return sent

    return asyncio.run(scenario())


def _problem(sent: list[Message]) -> dict[str, Any]:
    """Decode the body from one complete problem response."""

    assert sent[0]["type"] == "http.response.start"
    assert sent[1]["type"] == "http.response.body"
    return json.loads(sent[1]["body"])


def test_constructor_requires_positive_limit() -> None:
    async def app(_scope: Scope, _receive: Receive, _send: Send) -> None:
        return None

    with pytest.raises(ValueError, match="positive"):
        RequestBoundaryMiddleware(app, maximum_body_bytes=0)


@pytest.mark.parametrize(
    "headers,error_code,status_code",
    [
        (
            [(b"content-length", b"1"), (b"Content-Length", b"1")],
            "invalid_content_length",
            400,
        ),
        ([(b"content-length", b"not-a-number")], "invalid_content_length", 400),
        ([(b"content-length", b"-1")], "invalid_content_length", 400),
        ([(b"content-length", b"6")], "request_body_too_large", 413),
        ([(b"content-length", "é".encode())], "invalid_content_length", 400),
    ],
)
def test_declared_length_failures_are_rejected_before_dispatch(
    headers: list[tuple[bytes, bytes]],
    error_code: str,
    status_code: int,
) -> None:
    called = False

    async def app(_scope: Scope, _receive: Receive, _send: Send) -> None:
        nonlocal called
        called = True

    sent = _run(
        _middleware(app, 5),
        _http_scope(headers),
        [{"type": "http.request", "body": b"", "more_body": False}],
    )

    assert called is False
    assert sent[0]["status"] == status_code
    problem = _problem(sent)
    assert problem["error_code"] == error_code
    assert problem["support_reference"] == str(SUPPORT_REFERENCE)
    assert problem["next_action"]
    assert "trace_reference" not in problem
    headers_map = dict(sent[0]["headers"])
    assert headers_map[b"x-support-reference"] == str(SUPPORT_REFERENCE).encode()
    assert b"x-request-id" not in headers_map
    assert headers_map[b"content-type"] == b"application/problem+json"


def test_actual_streamed_bytes_cannot_bypass_missing_length() -> None:
    async def app(_scope: Scope, receive: Receive, send: Send) -> None:
        while True:
            message = await receive()
            if not message.get("more_body", False):
                break
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    sent = _run(
        _middleware(app, 5),
        _http_scope(),
        [
            {"type": "http.request", "body": b"abc", "more_body": True},
            {"type": "http.request", "body": b"def", "more_body": False},
        ],
    )

    assert sent[0]["status"] == 413
    problem = _problem(sent)
    assert problem["error_code"] == "request_body_too_large"
    assert problem["support_reference"] == str(SUPPORT_REFERENCE)
    assert str(TRACE_REFERENCE) not in json.dumps(problem)


def test_exact_limit_passes_and_security_headers_are_added_once() -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        assert scope["state"]["trace_reference"] == TRACE_REFERENCE
        assert scope["state"]["support_reference"] == SUPPORT_REFERENCE
        message = await receive()
        assert message["body"] == b"12345"
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"cache-control", b"private")],
            }
        )
        await send({"type": "http.response.body", "body": b"ok"})

    sent = _run(
        _middleware(app, 5),
        _http_scope([(b"content-length", b"5")]),
        [{"type": "http.request", "body": b"12345", "more_body": False}],
    )

    assert sent[0]["status"] == 200
    headers = sent[0]["headers"]
    assert headers.count((b"cache-control", b"private")) == 1
    assert (b"x-content-type-options", b"nosniff") in headers
    assert (b"referrer-policy", b"no-referrer") in headers
    assert (b"x-support-reference", str(SUPPORT_REFERENCE).encode()) in headers
    assert not any(name.lower() == b"x-request-id" for name, _value in headers)


def test_non_http_protocol_is_passed_through() -> None:
    called = False

    async def app(scope: Scope, _receive: Receive, _send: Send) -> None:
        nonlocal called
        called = True
        assert scope["type"] == "lifespan"

    middleware = RequestBoundaryMiddleware(app)
    sent = _run(
        middleware,
        {"type": "lifespan", "asgi": {"version": "3.0"}},
        [],
    )

    assert called is True
    assert sent == []


def test_crossing_limit_after_response_start_fails_closed() -> None:
    async def app(_scope: Scope, receive: Receive, send: Send) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await receive()

    middleware = _middleware(app, 2)

    with pytest.raises(RuntimeError, match="after response start"):
        _run(
            middleware,
            _http_scope(),
            [{"type": "http.request", "body": b"too large", "more_body": False}],
        )
