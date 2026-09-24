"""Validate and emit core ASGI HTTP response events without hiding server lifecycle failures."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import inspect
from typing import cast

AsgiSend = Callable[[dict[str, object]], Awaitable[None]]
_CORE_HTTP_RESPONSE_EVENT_TYPES = frozenset({"http.response.start", "http.response.body"})
_HTTP_FIELD_NAME_OCTETS = frozenset(
    b"!#$%&'*+-.^_`|~0123456789abcdefghijklmnopqrstuvwxyz"
)
_NO_CONTENT_FINAL_STATUSES = frozenset({204, 205, 304})


class CompositionResponseEventError(ValueError):
    """Raised when a caller-owned outbound event violates this core HTTP response contract."""


class CompositionResponseSendError(RuntimeError):
    """Raised when an injected ASGI send capability cannot satisfy its call contract."""


def _require_http_field_name(name: bytes) -> None:
    """Require one lowercased RFC 9110 token before handing a header to the ASGI server."""

    if not name or any(octet not in _HTTP_FIELD_NAME_OCTETS for octet in name):
        raise CompositionResponseEventError(
            "ASGI http.response.start header names must be non-empty lowercase HTTP tokens"
        )


def _require_http_field_value(value: bytes) -> None:
    """Reject HTTP field-value control octets that are invalid or dangerous on the wire."""

    if any((octet < 0x20 and octet != 0x09) or octet == 0x7F for octet in value):
        raise CompositionResponseEventError(
            "ASGI http.response.start header values must not contain invalid HTTP control octets"
        )


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
        _require_http_field_name(name)
        _require_http_field_value(value)


def _require_response_start(event: dict[str, object]) -> None:
    """Validate core response-start fields and reject trailer promises this owner cannot finish."""

    status = event.get("status")
    if type(status) is not int or not 100 <= status <= 599:
        raise CompositionResponseEventError(
            "ASGI http.response.start status must be an integer HTTP status code from 100 to 599"
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


def _require_complete_content_length(
    *,
    status: int,
    headers: list[object],
    representation_body: bytes,
) -> None:
    """Bind one explicit Content-Length to RFC 9110 final-response framing semantics."""

    values: list[bytes] = []
    for pair in headers:
        header_pair = cast(list[bytes] | tuple[bytes, bytes], pair)
        name, value = header_pair
        if name == b"content-length":
            values.append(value)
    if not values:
        return
    if len(values) != 1:
        raise CompositionResponseEventError(
            "complete ASGI response content-length must appear at most once"
        )
    if status == 204:
        raise CompositionResponseEventError(
            "complete ASGI 204 response must not include content-length"
        )

    value = values[0]
    if not value or not value.isdigit():
        raise CompositionResponseEventError(
            "complete ASGI response content-length must be one decimal byte string"
        )
    normalized_value = value.lstrip(b"0") or b"0"
    expected_octets = 0 if status == 205 else len(representation_body)
    if normalized_value != str(expected_octets).encode("ascii"):
        raise CompositionResponseEventError(
            "complete ASGI response content-length does not match response semantics"
        )


async def send_asgi_response_event(send: object, event: object) -> None:
    """Send one validated core HTTP response event without reclassifying server failures.

    The caller-owned event is validated before server invocation. This owner accepts only exact
    dictionaries for ``http.response.start`` and ``http.response.body`` and validates their core
    ASGI field shapes. Response status must remain in RFC 9110's valid 100..599 range. Header names
    are constrained to lowercased HTTP tokens and invalid control octets are rejected from values
    before an HTTP implementation can parse them inconsistently. A response-start trailer promise
    is rejected because this boundary does not yet own ``http.response.trailers`` emission;
    extension or trailer support requires an explicit scope-aware successor rather than silently
    widening this contract.

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


async def send_complete_http_response(
    send: object,
    *,
    status: object,
    headers: object,
    body: object,
    suppress_body: object = False,
) -> None:
    """Emit one final non-streaming HTTP response after validating both core events.

    Informational 1xx messages are not terminal responses and remain outside this completion
    boundary. Both response-start and terminal response-body are validated before ``send`` is
    invoked, so malformed caller-owned body material cannot be discovered only after response-start
    has made the response irreversible. ``suppress_body`` supports HEAD-style content suppression
    without changing representation metadata; RFC 9110 no-content statuses 204, 205, and 304
    suppress representation bytes independently. An explicit Content-Length is accepted only when
    it is unique and consistent with the selected representation, except that 204 forbids the field
    and 205 can only describe the zero-octet response. The underlying representation body must still
    be bytes so HEAD/304 metadata can be checked against the response this owner would otherwise send.

    Server/runtime failures raised while sending either event propagate unchanged. The helper does
    not retry, remap, or manufacture a second response after partial emission.
    """

    if type(status) is not int or not 200 <= status <= 599:
        raise CompositionResponseEventError(
            "complete ASGI final response status must be an integer HTTP status code from 200 to 599"
        )
    if type(suppress_body) is not bool:
        raise CompositionResponseEventError(
            "complete ASGI response suppress_body must be a boolean"
        )
    if type(body) is not bytes:
        raise CompositionResponseEventError("ASGI http.response.body body must be bytes")

    response_headers = list(headers) if type(headers) in (list, tuple) else headers
    start_event: dict[str, object] = {
        "type": "http.response.start",
        "status": status,
        "headers": response_headers,
    }
    body_event: dict[str, object] = {
        "type": "http.response.body",
        "body": b""
        if suppress_body or status in _NO_CONTENT_FINAL_STATUSES
        else body,
        "more_body": False,
    }

    _require_core_http_response_event(start_event)
    _require_core_http_response_event(body_event)
    _require_complete_content_length(
        status=status,
        headers=cast(list[object], response_headers),
        representation_body=body,
    )
    await send_asgi_response_event(send, start_event)
    await send_asgi_response_event(send, body_event)
