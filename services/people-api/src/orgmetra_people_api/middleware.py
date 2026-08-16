"""ASGI request-boundary middleware for size, tracing, and safe headers."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from uuid import UUID, uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send

IdentifierFactory = Callable[[], UUID]


class _BodyLimitExceeded(RuntimeError):
    """Signal that streamed request bytes crossed the configured limit."""


class RequestBoundaryMiddleware:
    """Enforce finite requests while separating operator and client references."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        maximum_body_bytes: int = 65_536,
        identifier_factory: IdentifierFactory = uuid4,
        support_identifier_factory: IdentifierFactory = uuid4,
    ) -> None:
        """Configure a positive byte limit and independent identifier sources."""

        if maximum_body_bytes <= 0:
            raise ValueError("maximum_body_bytes must be positive")
        self._app = app
        self._maximum_body_bytes = maximum_body_bytes
        self._identifier_factory = identifier_factory
        self._support_identifier_factory = support_identifier_factory

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Apply the boundary to HTTP traffic and pass through other protocols."""

        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        trace_reference = self._identifier_factory()
        support_reference = self._support_identifier_factory()
        state = scope.setdefault("state", {})
        state["trace_reference"] = trace_reference
        state["support_reference"] = support_reference

        content_lengths = [
            value
            for name, value in scope.get("headers", [])
            if name.lower() == b"content-length"
        ]
        if len(content_lengths) > 1:
            await self._send_problem(
                scope,
                send,
                support_reference,
                status_code=400,
                error_code="invalid_content_length",
                title="Invalid Content-Length",
                detail="The request contains conflicting Content-Length headers.",
                next_action="Send exactly one valid Content-Length header and retry.",
            )
            return
        if content_lengths:
            try:
                declared_length = int(content_lengths[0].decode("ascii"), 10)
            except (UnicodeDecodeError, ValueError):
                declared_length = -1
            if declared_length < 0:
                await self._send_problem(
                    scope,
                    send,
                    support_reference,
                    status_code=400,
                    error_code="invalid_content_length",
                    title="Invalid Content-Length",
                    detail="Content-Length must be a non-negative ASCII integer.",
                    next_action="Send a non-negative ASCII Content-Length value and retry.",
                )
                return
            if declared_length > self._maximum_body_bytes:
                await self._send_problem(
                    scope,
                    send,
                    support_reference,
                    status_code=413,
                    error_code="request_body_too_large",
                    title="Request body too large",
                    detail="The request body exceeds the configured byte limit.",
                    next_action="Submit a smaller request body and retry.",
                )
                return

        consumed_bytes = 0
        response_started = False

        async def bounded_receive() -> Message:
            """Count actual body bytes so framing cannot bypass the limit."""

            nonlocal consumed_bytes
            message = await receive()
            if message["type"] == "http.request":
                consumed_bytes += len(message.get("body", b""))
                if consumed_bytes > self._maximum_body_bytes:
                    raise _BodyLimitExceeded
            return message

        async def secure_send(message: Message) -> None:
            """Attach client-safe support and defensive response headers once."""

            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
                headers = list(message.get("headers", []))
                header_names = {name.lower() for name, _value in headers}
                additions = {
                    b"cache-control": b"no-store",
                    b"x-content-type-options": b"nosniff",
                    b"referrer-policy": b"no-referrer",
                    b"x-support-reference": str(support_reference).encode("ascii"),
                }
                headers.extend(
                    (name, value)
                    for name, value in additions.items()
                    if name not in header_names
                )
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self._app(scope, bounded_receive, secure_send)
        except _BodyLimitExceeded:
            if response_started:
                raise RuntimeError(
                    "request body limit was crossed after response start"
                ) from None
            await self._send_problem(
                scope,
                send,
                support_reference,
                status_code=413,
                error_code="request_body_too_large",
                title="Request body too large",
                detail="The request body exceeds the configured byte limit.",
                next_action="Submit a smaller request body and retry.",
            )

    async def _send_problem(
        self,
        scope: Scope,
        send: Send,
        support_reference: UUID,
        *,
        status_code: int,
        error_code: str,
        title: str,
        detail: str,
        next_action: str,
    ) -> None:
        """Send a pre-dispatch problem without exposing internal trace identity."""

        payload = json.dumps(
            {
                "type": f"urn:orgmetra:problem:{error_code}",
                "title": title,
                "status": status_code,
                "detail": detail,
                "instance": scope.get("path", "/"),
                "error_code": error_code,
                "support_reference": str(support_reference),
                "next_action": next_action,
            },
            separators=(",", ":"),
        ).encode("utf-8")
        headers = [
            (b"content-type", b"application/problem+json"),
            (b"content-length", str(len(payload)).encode("ascii")),
            (b"cache-control", b"no-store"),
            (b"x-content-type-options", b"nosniff"),
            (b"referrer-policy", b"no-referrer"),
            (b"x-support-reference", str(support_reference).encode("ascii")),
        ]
        await send(
            {
                "type": "http.response.start",
                "status": status_code,
                "headers": headers,
            }
        )
        await send({"type": "http.response.body", "body": payload})
