"""Invoke ASGI HTTP response-send capabilities without hiding server lifecycle failures."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import inspect
from typing import cast

AsgiSend = Callable[[dict[str, object]], Awaitable[None]]
_CORE_HTTP_RESPONSE_EVENT_TYPES = frozenset({"http.response.start", "http.response.body"})


class CompositionResponseEventError(ValueError):
    """Raised when a caller attempts to emit a non-core HTTP response event."""


class CompositionResponseSendError(RuntimeError):
    """Raised when an injected ASGI send capability cannot satisfy its call contract."""


def _require_core_http_response_event(event: object) -> dict[str, object]:
    """Return an exact ASGI event dict only when it belongs to the core HTTP response channel."""

    if type(event) is not dict:
        raise CompositionResponseEventError("ASGI HTTP response event must be an exact dict")
    response_event = cast(dict[str, object], event)
    event_type = response_event.get("type")
    if type(event_type) is not str or event_type not in _CORE_HTTP_RESPONSE_EVENT_TYPES:
        raise CompositionResponseEventError(
            "ASGI HTTP response event type must be http.response.start or http.response.body"
        )
    return response_event


async def send_asgi_response_event(send: object, event: object) -> None:
    """Send one validated core HTTP response event without reclassifying server failures.

    The local boundary proves only facts it can observe directly. The outbound message must be an
    exact dictionary whose ``type`` is one of the core HTTP response events owned here; inbound,
    foreign-protocol, extension, missing, and non-string event types fail before server invocation.
    The ``send`` capability must be callable and its normal return must be awaitable. Exceptions
    raised by invoking a callable are not sufficient evidence of a local configuration defect and
    therefore propagate unchanged, as do every exception and cancellation raised while awaiting a
    valid result. This preserves ASGI server authority for closed-connection ``OSError`` and other
    protocol/runtime failures while preventing the composition layer from emitting a request or
    foreign-protocol event through its HTTP response channel.
    """

    response_event = _require_core_http_response_event(event)
    if not callable(send):
        raise CompositionResponseSendError("ASGI send must be callable")
    send_callable = cast(Callable[[dict[str, object]], object], send)
    pending_send = send_callable(response_event)
    if not inspect.isawaitable(pending_send):
        raise CompositionResponseSendError("ASGI send result must be awaitable")
    await pending_send
