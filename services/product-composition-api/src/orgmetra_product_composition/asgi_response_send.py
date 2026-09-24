"""Invoke ASGI response-send capabilities without hiding server lifecycle failures."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import inspect
from typing import cast

AsgiSend = Callable[[dict[str, object]], Awaitable[None]]


class CompositionResponseSendError(RuntimeError):
    """Raised when an injected ASGI send capability cannot satisfy its call contract."""


async def send_asgi_response_event(send: object, event: dict[str, object]) -> None:
    """Send one caller-owned ASGI response event through a validated async capability.

    The boundary proves only capability shape: ``send`` must be callable and its normal return must
    be awaitable. Exceptions raised by invoking a callable are not sufficient evidence of a local
    configuration defect and therefore propagate unchanged, as do every exception and cancellation
    raised while awaiting a valid result. This preserves ASGI server authority for closed-connection
    ``OSError`` and other protocol/runtime failures while still rejecting demonstrably malformed
    injected capabilities before awaiting them.
    """

    if not callable(send):
        raise CompositionResponseSendError("ASGI send must be callable")
    send_callable = cast(Callable[[dict[str, object]], object], send)
    pending_send = send_callable(event)
    if not inspect.isawaitable(pending_send):
        raise CompositionResponseSendError("ASGI send result must be awaitable")
    await pending_send
