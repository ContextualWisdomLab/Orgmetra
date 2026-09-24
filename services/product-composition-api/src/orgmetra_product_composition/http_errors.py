"""Map composition transport/routing failures to stable non-disclosing HTTP responses."""

from __future__ import annotations

from dataclasses import dataclass
import json

from .asgi_response_send import AsgiSend, send_asgi_response_event
from .request_routing import (
    CompositionMethodNotAllowedError,
    CompositionMethodNotImplementedError,
    CompositionRequestError,
    CompositionRouteNotFoundError,
    CompositionRouteUnavailableError,
    CompositionRoutingError,
    _require_method_rejection_authority,
)


@dataclass(frozen=True, slots=True)
class CompositionHttpResponse:
    """One deterministic error response safe to emit at the composition HTTP boundary."""

    status: int
    headers: tuple[tuple[bytes, bytes], ...]
    body: bytes


def _problem_response(
    *,
    status: int,
    code: str,
    title: str,
    extra_headers: tuple[tuple[bytes, bytes], ...] = (),
) -> CompositionHttpResponse:
    """Build a bounded RFC 9457-compatible problem response without internal exception text."""

    body = json.dumps(
        {
            "type": "about:blank",
            "title": title,
            "status": status,
            "code": code,
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return CompositionHttpResponse(
        status=status,
        headers=(
            (b"content-type", b"application/problem+json"),
            (b"cache-control", b"no-store"),
            *extra_headers,
        ),
        body=body,
    )


def _allow_header_value(error: CompositionMethodNotAllowedError) -> bytes:
    """Serialize only the construction-time 405 authority issued with this error."""

    issued_methods = _require_method_rejection_authority(error)
    return ", ".join(issued_methods).encode("ascii")


def http_response_for_composition_error(error: Exception) -> CompositionHttpResponse:
    """Map one known composition failure to a stable HTTP response or reject foreign failures."""

    if isinstance(error, CompositionMethodNotAllowedError):
        return _problem_response(
            status=405,
            code="method_not_allowed",
            title="Method Not Allowed",
            extra_headers=((b"allow", _allow_header_value(error)),),
        )
    if isinstance(error, CompositionRequestError):
        return _problem_response(
            status=400,
            code="invalid_request",
            title="Bad Request",
        )
    if isinstance(error, CompositionMethodNotImplementedError):
        return _problem_response(
            status=501,
            code="method_not_implemented",
            title="Not Implemented",
        )
    if isinstance(error, CompositionRouteNotFoundError):
        return _problem_response(
            status=404,
            code="route_not_found",
            title="Not Found",
        )
    if isinstance(error, CompositionRouteUnavailableError):
        return _problem_response(
            status=503,
            code="route_unavailable",
            title="Service Unavailable",
        )
    if isinstance(error, CompositionRoutingError):
        return _problem_response(
            status=500,
            code="routing_error",
            title="Internal Server Error",
        )
    raise TypeError("error must be a product-composition routing failure")


async def send_composition_error_response(
    send: AsgiSend,
    error: Exception,
    *,
    request_method: object,
) -> None:
    """Emit one complete ASGI error response while preserving HEAD no-content semantics.

    The raw request method is required because malformed requests can fail before method
    canonicalization. Only an exact built-in ``HEAD`` value suppresses response content; every
    other value receives the mapped problem body so an invalid method can still get a useful 400.
    Outbound ASGI capability-shape failures are rejected before await, while await-side server
    lifecycle errors such as a closed-connection ``OSError`` and task cancellation propagate.
    """

    response = http_response_for_composition_error(error)
    await send_asgi_response_event(
        send,
        {
            "type": "http.response.start",
            "status": response.status,
            "headers": list(response.headers),
        },
    )
    await send_asgi_response_event(
        send,
        {
            "type": "http.response.body",
            "body": b""
            if type(request_method) is str and request_method == "HEAD"
            else response.body,
            "more_body": False,
        },
    )
