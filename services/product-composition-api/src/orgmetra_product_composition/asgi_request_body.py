"""Consume ASGI HTTP request bodies with explicit bounds and lifecycle failure semantics."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from .asgi_transport import CompositionTransportError

_MAX_REQUEST_BODY_BYTES = 16 * 1024 * 1024


class CompositionRequestBodyError(CompositionTransportError):
    """Raised when ASGI request-body evidence is malformed or its local contract is invalid."""


class CompositionRequestBodyTooLargeError(CompositionRequestBodyError):
    """Raised when accumulated request content exceeds the configured hard byte limit."""


class CompositionClientDisconnectedError(CompositionTransportError):
    """Raised when the ASGI server reports that the client disconnected before body completion."""


async def read_bounded_http_request_body(
    receive: Callable[[], Awaitable[object]],
    *,
    max_body_bytes: int,
) -> bytes:
    """Return one detached HTTP request body without inventing timeout or disconnect semantics.

    ASGI defines omitted ``body`` as ``b""`` and omitted ``more_body`` as ``False``. Those defaults
    are accepted, while supplied values must use exact built-in ``bytes`` and ``bool`` values.
    ``http.disconnect`` remains a distinct lifecycle signal so a future host can stop work instead
    of trying to serialize an HTTP error to a peer that is already gone. Task cancellation is not
    caught here; caller/server cancellation therefore propagates unchanged.
    """

    if type(max_body_bytes) is not int or not 0 <= max_body_bytes <= _MAX_REQUEST_BODY_BYTES:
        raise CompositionRequestBodyError(
            "max_body_bytes must be an exact integer between 0 and 16777216"
        )
    if not callable(receive):
        raise CompositionRequestBodyError("ASGI receive must be callable")

    chunks: list[bytes] = []
    accumulated_bytes = 0
    while True:
        event = await receive()
        if type(event) is not dict:
            raise CompositionRequestBodyError("ASGI receive event must be an exact built-in dict")

        event_type = event.get("type")
        if type(event_type) is not str:
            raise CompositionRequestBodyError("ASGI receive event type must be an exact built-in str")
        if event_type == "http.disconnect":
            raise CompositionClientDisconnectedError(
                "client disconnected before the HTTP request body completed"
            )
        if event_type != "http.request":
            raise CompositionRequestBodyError(
                "ASGI receive event must be http.request or http.disconnect"
            )

        body = event.get("body", b"")
        more_body = event.get("more_body", False)
        if type(body) is not bytes:
            raise CompositionRequestBodyError("ASGI http.request body must be exact built-in bytes")
        if type(more_body) is not bool:
            raise CompositionRequestBodyError(
                "ASGI http.request more_body must be an exact built-in bool"
            )

        accumulated_bytes += len(body)
        if accumulated_bytes > max_body_bytes:
            raise CompositionRequestBodyTooLargeError(
                "ASGI HTTP request body exceeds the configured byte limit"
            )
        if body:
            chunks.append(body)
        if not more_body:
            return b"".join(chunks)
