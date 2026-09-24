"""Invoke ASGI response-send capabilities without hiding server lifecycle failures."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import inspect

AsgiSend = Callable[[dict[str, object]], Awaitable[None]]


class CompositionResponseSendError(RuntimeError):
    """Raised when an injected ASGI send capability cannot satisfy its call contract."""


async def send_asgi_response_event(send: object, event: dict[str, object]) -> None:
    """Send one caller-owned ASGI response event through a validated async capability.

    Capability-shape failures that happen before an awaitable exists are local composition
    configuration errors. Once an awaitable exists, its exceptions remain server/caller lifecycle
    authority. In particular, a server-specific ``OSError`` for a closed connection and task
    cancellation must propagate unchanged so the eventual ASGI host can stop work and clean up
    rather than attempt to serialize a second response.
    """

    if not callable(send):
        raise CompositionResponseSendError("ASGI send must be callable")
    try:
        pending_send = send(event)
    except Exception as exc:
        raise CompositionResponseSendError(
            "ASGI send invocation must return an awaitable without synchronous failure"
        ) from exc
    if not inspect.isawaitable(pending_send):
        raise CompositionResponseSendError("ASGI send result must be awaitable")
    await pending_send
