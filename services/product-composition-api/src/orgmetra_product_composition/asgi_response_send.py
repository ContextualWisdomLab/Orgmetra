"""Validate and emit core ASGI HTTP response events without hiding server lifecycle failures."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import inspect
from typing import cast

AsgiSend = Callable[[dict[str, object]], Awaitable[None]]
_CORE_HTTP_RESPONSE_EVENT_TYPES = frozenset({"http.response.start", "http.response.body"})


class CompositionResponseEventError(ValueError):
    """Raised when a caller-owned outbound event violates this core HTTP response contract."""


class CompositionResponseSendError(RuntimeError):
    """Raised when an injected ASGI send capability cannot satisfy its call contract."""


def _require_response_headers(headers: object) -> None:
    """Validate the finite header representation used by this composition response boundary."""

    if type(headers) not in (list, tuple):
        raise CompositionResponseEventError("ASGI http.response.start headers must be a list or tuple")
    for pair in headers:
        if type(pair) not in (list, tuple):
            raise CompositionResponseEventError(
                "ASGI http.response.start header entries must be two-item lists or tuples"
            )
        if len(pair) != 2:
            raise CompositionResponseEventError(
                "ASGI http.response.start header entries must contain exactly two items"
            )
        name, value = pair
        if type(name) is not bytes:
            raise CompositionResponseEventError(
                "ASGI http.response.start header names must be bytes"
            )
        if type(value) is not bytes:
            raise CompositionResponseEventError(
                "ASGI http.response.start header values must be bytes"
            )
        if name.startswith(b":"):
            raise CompositionResponseEventError(
                "ASGI http.response.start must not contain HTTP pseudo headers"
            )
        if name != name.lower():
            raise CompositionResponseEventError(
                "ASGI http.response.start header names must be lowercased"
            )


def _require_response_start(event: dict[str, object]) -> None:
    """Validate core response-start fields and reject trailer promises this owner cannot finish."""

    status = event.get("status")
    if type(status) is not int or not 100 <= status <= 999:
        raise CompositionResponseEventError(
            "ASGI http.response.start status must be an integer three-digit HTTP status code"
        )
    _require_response_headers(event.get("headers", []))
    trailers = event.get("trailers", False)
    if type(trailers) is not bool:
        raise CompositionResponseEventError(
            "ASGI http.response.start trailers must be a boolean when present"
        )
    if trailers:
        raise CompositionResponseEventError(
            "ASGI http.response.start trailers=True is unsupported until trailer emission is owned"
        )


def _require_response_body(event: dict[str, object]) -> None:
    """Validate core response-body optional fields while preserving their ASGI defaults."""

    body = event.get("body", b"")
    if type(body) is not bytes:
        raise CompositionResponseEventError("ASGI http.response.body body must be bytes")
    more_body = event.get("more_body", False)
    if type(more_body) is not bool:
        raise CompositionResponseEventError("ASGI http.response.body more_body must be a boolean")


def _require_core_http_response_event(event: object) -> dict[str, object]:
    """Return an exact event dict only when its core HTTP response shape is valid here."""

    if type(event) is not dict:
        raise CompositionResponseEventError("ASGI HTTP response event must be an exact dict")
    response_event = cast(dict[str, object], event)
    event_type = response_event.get("type")
    if type(event_type) is not str or event_type not in _CORE_HTTP_RESPONSE_EVENT_TYPES:
        raise CompositionResponseEventError(
            "ASGI HTTP response event type must be http.response.start or http.response.body"
        )
    if event_type == "http.response.start":
        _require_response_start(response_event)
    else:
        _require_response_body(response_event)
    return response_event


async def send_asgi_response_event(send: object, event: object) -> None:
    """Send one validated core HTTP response event without reclassifying server failures.

    The caller-owned event is validated before server invocation. This owner accepts only exact
    dictionaries for ``http.response.start`` and ``http.response.body`` and validates their core
    ASGI field shapes. A response-start trailer promise is rejected because this boundary does not
    yet own ``http.response.trailers`` emission; extension or trailer support requires an explicit
    scope-aware successor rather than silently widening this contract.

    The injected ``send`` capability must be callable and its normal return must be awaitable.
    Exceptions raised by invoking a callable are not sufficient evidence of a local configuration
    defect and therefore propagate unchanged, as do every exception and cancellation raised while
    awaiting a valid result. This preserves ASGI server authority for closed-connection ``OSError``
    and other protocol/runtime failures while preventing malformed or wrong-direction messages from
    reaching the HTTP response channel.
    """

    response_event = _require_core_http_response_event(event)
    if not callable(send):
        raise CompositionResponseSendError("ASGI send must be callable")
    send_callable = cast(Callable[[dict[str, object]], object], send)
    pending_send = send_callable(response_event)
    if not inspect.isawaitable(pending_send):
        raise CompositionResponseSendError("ASGI send result must be awaitable")
    await pending_send
