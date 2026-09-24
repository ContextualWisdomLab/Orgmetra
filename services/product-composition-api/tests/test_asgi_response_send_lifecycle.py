from __future__ import annotations

import asyncio

import pytest

from orgmetra_product_composition import CompositionRouteNotFoundError, send_composition_error_response
from orgmetra_product_composition.asgi_response_send import (
    CompositionResponseEventError,
    CompositionResponseSendError,
    send_asgi_response_event,
)


def _response_start_event() -> dict[str, object]:
    """Return one valid ASGI response-start event for send-boundary tests."""

    return {
        "type": "http.response.start",
        "status": 204,
        "headers": [(b"content-type", b"text/plain")],
    }


def _response_body_event() -> dict[str, object]:
    """Return one valid ASGI response-body event for send-boundary tests."""

    return {"type": "http.response.body", "body": b"", "more_body": False}


def test_asgi_send_rejects_non_callable_capability() -> None:
    """Reject a non-callable send capability before any transport work is attempted."""

    with pytest.raises(CompositionResponseSendError, match="callable"):
        asyncio.run(send_asgi_response_event(object(), _response_start_event()))


def test_asgi_send_preserves_synchronous_invocation_failure() -> None:
    """Preserve a server failure raised before an awaitable exists instead of reclassifying it."""

    failure = RuntimeError("sync server send failure")
    calls = 0

    def send(_: dict[str, object]) -> object:
        nonlocal calls
        calls += 1
        raise failure

    with pytest.raises(RuntimeError) as caught:
        asyncio.run(send_asgi_response_event(send, _response_start_event()))

    assert calls == 1
    assert caught.value is failure


def test_asgi_send_preserves_synchronous_closed_connection_oserror() -> None:
    """Preserve a server closed-connection OSError even when raised before an awaitable exists."""

    closed = BrokenPipeError("peer closed before awaitable")
    calls = 0

    def send(_: dict[str, object]) -> object:
        nonlocal calls
        calls += 1
        raise closed

    with pytest.raises(BrokenPipeError) as caught:
        asyncio.run(send_asgi_response_event(send, _response_start_event()))

    assert calls == 1
    assert caught.value is closed


def test_asgi_send_rejects_non_awaitable_result() -> None:
    """Reject a callable whose synchronous result does not satisfy the ASGI awaitable contract."""

    calls = 0

    def send(_: dict[str, object]) -> object:
        nonlocal calls
        calls += 1
        return {"not": "awaitable"}

    with pytest.raises(CompositionResponseSendError, match="awaitable"):
        asyncio.run(send_asgi_response_event(send, _response_start_event()))

    assert calls == 1


def test_asgi_send_preserves_closed_connection_oserror_from_awaitable() -> None:
    """Preserve the server's closed-connection OSError instead of laundering lifecycle failure."""

    closed = ConnectionResetError("peer closed")

    async def send(_: dict[str, object]) -> None:
        raise closed

    with pytest.raises(ConnectionResetError) as caught:
        asyncio.run(send_asgi_response_event(send, _response_start_event()))

    assert caught.value is closed


def test_asgi_send_preserves_cancellation_from_awaitable() -> None:
    """Leave task cancellation under caller/server lifecycle authority."""

    async def send(_: dict[str, object]) -> None:
        raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(send_asgi_response_event(send, _response_start_event()))


def test_asgi_send_rejects_non_dict_response_event_before_transport() -> None:
    """Reject a non-dict outbound message before invoking the ASGI server capability."""

    calls = 0

    async def send(_: dict[str, object]) -> None:
        nonlocal calls
        calls += 1

    with pytest.raises(CompositionResponseEventError, match="dict"):
        asyncio.run(send_asgi_response_event(send, object()))

    assert calls == 0


@pytest.mark.parametrize("event_type", [None, 17, "http.request", "websocket.send"])
def test_asgi_send_rejects_non_http_response_event_type_before_transport(event_type: object) -> None:
    """Keep inbound, foreign-protocol, missing, and non-string event types off the response channel."""

    calls = 0

    async def send(_: dict[str, object]) -> None:
        nonlocal calls
        calls += 1

    with pytest.raises(CompositionResponseEventError, match="http.response"):
        asyncio.run(send_asgi_response_event(send, {"type": event_type}))

    assert calls == 0


@pytest.mark.parametrize(
    "event",
    [
        {"type": "http.response.start"},
        {"type": "http.response.start", "status": True},
        {"type": "http.response.start", "status": 99},
        {"type": "http.response.start", "status": 1000},
        {"type": "http.response.start", "status": 200, "headers": "not-headers"},
        {"type": "http.response.start", "status": 200, "headers": [b"not-a-pair"]},
        {"type": "http.response.start", "status": 200, "headers": [(b"only-one",)]},
        {"type": "http.response.start", "status": 200, "headers": [("x-name", b"value")]},
        {"type": "http.response.start", "status": 200, "headers": [(b"x-name", "value")]},
        {"type": "http.response.start", "status": 200, "headers": [(b"X-Name", b"value")]},
        {"type": "http.response.start", "status": 200, "headers": [(b":status", b"200")]},
        {"type": "http.response.start", "status": 200, "trailers": 1},
        {"type": "http.response.start", "status": 200, "trailers": True},
    ],
)
def test_asgi_send_rejects_malformed_or_unsupported_response_start_before_transport(
    event: dict[str, object],
) -> None:
    """Reject invalid start metadata and trailer promises that this owner cannot complete."""

    calls = 0

    async def send(_: dict[str, object]) -> None:
        nonlocal calls
        calls += 1

    with pytest.raises(CompositionResponseEventError, match="response.start"):
        asyncio.run(send_asgi_response_event(send, event))

    assert calls == 0


@pytest.mark.parametrize(
    "event",
    [
        {"type": "http.response.body", "body": "not-bytes"},
        {"type": "http.response.body", "more_body": 1},
    ],
)
def test_asgi_send_rejects_malformed_response_body_before_transport(
    event: dict[str, object],
) -> None:
    """Reject body fields whose runtime types violate the core ASGI HTTP contract."""

    calls = 0

    async def send(_: dict[str, object]) -> None:
        nonlocal calls
        calls += 1

    with pytest.raises(CompositionResponseEventError, match="response.body"):
        asyncio.run(send_asgi_response_event(send, event))

    assert calls == 0


@pytest.mark.parametrize("event", [_response_start_event(), _response_body_event()])
def test_asgi_send_accepts_well_formed_core_http_response_events(event: dict[str, object]) -> None:
    """Allow both well-formed core HTTP response message types through the validated boundary."""

    events: list[dict[str, object]] = []

    async def send(message: dict[str, object]) -> None:
        events.append(message)

    asyncio.run(send_asgi_response_event(send, event))

    assert events == [event]


def test_asgi_send_accepts_response_body_defaults() -> None:
    """Preserve ASGI's empty-body and final-body defaults when optional body fields are omitted."""

    events: list[dict[str, object]] = []

    async def send(message: dict[str, object]) -> None:
        events.append(message)

    event = {"type": "http.response.body"}
    asyncio.run(send_asgi_response_event(send, event))

    assert events == [event]


def test_error_response_uses_validated_send_capability() -> None:
    """Route existing problem-response emission through the same outbound capability boundary."""

    def send(_: dict[str, object]) -> object:
        return None

    with pytest.raises(CompositionResponseSendError, match="awaitable"):
        asyncio.run(
            send_composition_error_response(
                send,
                CompositionRouteNotFoundError("do not disclose"),
                request_method="GET",
            )
        )


def test_send_capability_failure_is_not_an_http_problem_mapping_input() -> None:
    """Prevent response-transport failure from recursively becoming another HTTP response."""

    from orgmetra_product_composition import http_response_for_composition_error

    with pytest.raises(TypeError, match="routing failure"):
        http_response_for_composition_error(CompositionResponseSendError("send failed"))
