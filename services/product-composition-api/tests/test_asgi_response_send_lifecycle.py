from __future__ import annotations

import asyncio

import pytest

from orgmetra_product_composition import CompositionRouteNotFoundError, send_composition_error_response
from orgmetra_product_composition.asgi_response_send import (
    CompositionResponseSendError,
    send_asgi_response_event,
)


def _response_start_event() -> dict[str, object]:
    """Return one inert ASGI response-start event for send-capability tests."""

    return {"type": "http.response.start", "status": 204, "headers": []}


def test_asgi_send_rejects_non_callable_capability() -> None:
    """Reject a non-callable send capability before any transport work is attempted."""

    with pytest.raises(CompositionResponseSendError, match="callable"):
        asyncio.run(send_asgi_response_event(object(), _response_start_event()))


def test_asgi_send_wraps_only_synchronous_invocation_failure() -> None:
    """Classify non-lifecycle failure before an awaitable exists as invalid send capability shape."""

    failure = RuntimeError("sync send failure")
    calls = 0

    def send(_: dict[str, object]) -> object:
        nonlocal calls
        calls += 1
        raise failure

    with pytest.raises(CompositionResponseSendError, match="invocation") as caught:
        asyncio.run(send_asgi_response_event(send, _response_start_event()))

    assert calls == 1
    assert caught.value.__cause__ is failure


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
