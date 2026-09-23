from __future__ import annotations

import asyncio
from collections.abc import Iterable

import pytest

from orgmetra_product_composition.asgi_request_body import (
    CompositionClientDisconnectedError,
    CompositionRequestBodyError,
    CompositionRequestBodyTooLargeError,
    read_bounded_http_request_body,
)


class _ReceiveSequence:
    """Return exact ASGI receive events in order and expose how many were consumed."""

    def __init__(self, events: Iterable[object]) -> None:
        """Detach the supplied event sequence for deterministic one-shot consumption."""

        self._events = iter(tuple(events))
        self.calls = 0

    async def __call__(self) -> object:
        """Return the next queued event and count the receive call."""

        self.calls += 1
        return next(self._events)


def test_empty_request_body_accepts_asgi_defaults() -> None:
    """Accept an omitted body and omitted more_body as the ASGI empty-body defaults."""

    receive = _ReceiveSequence(({"type": "http.request"},))

    assert asyncio.run(read_bounded_http_request_body(receive, max_body_bytes=0)) == b""
    assert receive.calls == 1


def test_chunked_request_body_is_detached_and_stops_after_terminal_chunk() -> None:
    """Join exact bytes and do not consume a later event after more_body becomes false."""

    receive = _ReceiveSequence(
        (
            {"type": "http.request", "body": b"abc", "more_body": True},
            {"type": "http.request", "body": b"def", "more_body": False},
            {"type": "http.disconnect"},
        )
    )

    assert asyncio.run(read_bounded_http_request_body(receive, max_body_bytes=6)) == b"abcdef"
    assert receive.calls == 2


def test_request_body_size_limit_accepts_exact_boundary() -> None:
    """Permit a body whose accumulated byte length equals the configured hard limit."""

    receive = _ReceiveSequence(
        (
            {"type": "http.request", "body": b"ab", "more_body": True},
            {"type": "http.request", "body": b"cd"},
        )
    )

    assert asyncio.run(read_bounded_http_request_body(receive, max_body_bytes=4)) == b"abcd"


def test_request_body_size_limit_fails_before_waiting_for_more_chunks() -> None:
    """Reject an oversized partial body immediately even when the sender advertises more data."""

    receive = _ReceiveSequence(
        (
            {"type": "http.request", "body": b"abc", "more_body": True},
            {"type": "http.request", "body": b"never-consumed"},
        )
    )

    with pytest.raises(CompositionRequestBodyTooLargeError, match="exceeds"):
        asyncio.run(read_bounded_http_request_body(receive, max_body_bytes=2))
    assert receive.calls == 1


def test_client_disconnect_is_distinct_from_malformed_transport() -> None:
    """Surface a peer disconnect as lifecycle state rather than an HTTP error candidate."""

    receive = _ReceiveSequence(({"type": "http.disconnect"},))

    with pytest.raises(CompositionClientDisconnectedError, match="disconnected"):
        asyncio.run(read_bounded_http_request_body(receive, max_body_bytes=16))


@pytest.mark.parametrize(
    "event",
    (
        None,
        [],
        {"type": 1},
        {"type": "websocket.receive"},
        {"type": "http.request", "body": bytearray(b"abc")},
        {"type": "http.request", "more_body": 1},
    ),
)
def test_malformed_receive_events_fail_closed(event: object) -> None:
    """Reject non-ASGI or non-exact built-in event fields before body bytes are trusted."""

    receive = _ReceiveSequence((event,))

    with pytest.raises(CompositionRequestBodyError):
        asyncio.run(read_bounded_http_request_body(receive, max_body_bytes=16))


@pytest.mark.parametrize("max_body_bytes", (True, -1, 16 * 1024 * 1024 + 1))
def test_body_limit_configuration_is_bounded_and_exact(max_body_bytes: object) -> None:
    """Reject ambiguous or operationally unbounded body-limit configuration before receive I/O."""

    receive = _ReceiveSequence(({"type": "http.request"},))

    with pytest.raises(CompositionRequestBodyError, match="max_body_bytes"):
        asyncio.run(
            read_bounded_http_request_body(
                receive,
                max_body_bytes=max_body_bytes,  # type: ignore[arg-type]
            )
        )
    assert receive.calls == 0


def test_receive_must_be_callable_before_any_io() -> None:
    """Reject a non-callable receive boundary before attempting request-body lifecycle I/O."""

    with pytest.raises(CompositionRequestBodyError, match="receive"):
        asyncio.run(
            read_bounded_http_request_body(
                object(),  # type: ignore[arg-type]
                max_body_bytes=16,
            )
        )


def test_receive_cancellation_propagates_without_timeout_reclassification() -> None:
    """Preserve task cancellation so callers can distinguish cancellation from protocol failure."""

    class _CancelledReceive:
        """Raise the task-cancellation signal when the ASGI server cancels receive."""

        async def __call__(self) -> object:
            """Raise CancelledError without wrapping it in a composition transport exception."""

            raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(read_bounded_http_request_body(_CancelledReceive(), max_body_bytes=16))
