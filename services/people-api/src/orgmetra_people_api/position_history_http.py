"""Dependency-light ASGI route for governed Position-history reads.

The transport adapter owns request parsing and client-safe responses. The
Position-history service remains responsible for purpose-bound authorization,
bitemporal integrity, and minimizing the fields returned to the caller.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
import re
from secrets import token_urlsafe
from typing import Mapping
from urllib.parse import parse_qsl
from uuid import UUID

from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy

from orgmetra_people_api.auth import (
    AuthenticationFailed,
    TokenAuthenticator,
    extract_bearer_token,
)
from orgmetra_people_api.http import (
    AsgiReceive,
    AsgiSend,
    _authorization_header,
    _send_json as _emit_json,
)
from orgmetra_people_api.position_history import (
    PositionHistoryIntegrityError,
    PositionHistoryReadPort,
    read_position_history,
)

_LOGGER = logging.getLogger(__name__)
_ROUTE_PREFIX = ("v1", "tenants")
_PURPOSE_PATTERN = re.compile(r"\A[a-z][a-z0-9]*(?:_[a-z0-9]+)*\Z", flags=re.ASCII)
_FIELD_PATTERN = re.compile(r"\A[a-z][a-z0-9]*(?:_[a-z0-9]+)*\Z", flags=re.ASCII)
_RFC3339_INSTANT_PATTERN = re.compile(
    r"\A\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z\Z",
    flags=re.ASCII,
)
_MAX_UUID_INT = (1 << 128) - 1
_REQUIRED_QUERY_KEYS = frozenset({"known_at", "purpose", "fields"})
_SUPPORT_REFERENCE_RANDOM_BYTES = 24


class _InvalidHttpRequest(ValueError):
    """Indicate malformed Position-history route input that must fail closed."""


@dataclass(frozen=True, slots=True)
class _ParsedPositionHistoryRequest:
    """Hold validated path and query values for one Position-history read."""

    tenant_record_id: UUID
    position_record_id: UUID
    known_at: datetime
    purpose_code: str
    requested_fields: frozenset[str]


async def _send_error(
    send: AsgiSend,
    *,
    status: int,
    error_code: str,
    message: str,
    extra_headers: tuple[tuple[bytes, bytes], ...] = (),
) -> None:
    """Emit a client-safe error envelope with an opaque support reference."""
    support_reference = f"err_{token_urlsafe(_SUPPORT_REFERENCE_RANDOM_BYTES)}"
    _LOGGER.info(
        "Position-history request rejected",
        extra={
            "error_code": error_code,
            "http_status": status,
            "support_reference": support_reference,
        },
    )
    await _emit_json(
        send,
        status=status,
        payload={
            "error": error_code,
            "error_code": error_code,
            "message": message,
            "next_action": message,
            "support_reference": support_reference,
        },
        extra_headers=extra_headers,
    )


@dataclass(frozen=True, slots=True)
class PositionHistoryAsgiApp:
    """Expose one tenant-scoped, read-only Position-history route.

    Supported route::

        GET /v1/tenants/{tenant_record_id}/positions/{position_record_id}/history
            ?known_at=YYYY-MM-DDTHH:MM:SSZ
            &purpose=workforce_position_review
            &fields=effective_from,position_status_code

    The app contains no web-framework dependency and returns only the
    purpose-authorized Position-history fields from the governed service.
    """

    authenticator: TokenAuthenticator
    policy: PurposeBoundAccessPolicy
    read_port: PositionHistoryReadPort

    def __post_init__(self) -> None:
        """Reject incomplete dependencies before serving protected data."""
        if not isinstance(self.authenticator, TokenAuthenticator):
            raise TypeError("authenticator must implement TokenAuthenticator")
        if not isinstance(self.policy, PurposeBoundAccessPolicy):
            raise TypeError("policy must be a PurposeBoundAccessPolicy")
        if not isinstance(self.read_port, PositionHistoryReadPort):
            raise TypeError("read_port must implement PositionHistoryReadPort")

    async def __call__(self, scope: Mapping[str, object], receive: AsgiReceive, send: AsgiSend) -> None:
        """Serve one HTTP request without exposing bearer tokens or internals."""
        del receive
        if scope.get("type") != "http":
            raise ValueError("PositionHistoryAsgiApp accepts only HTTP ASGI scopes")

        if scope.get("method") != "GET":
            await _send_error(
                send,
                status=405,
                error_code="method_not_allowed",
                message="Use GET for the governed Position-history read route.",
                extra_headers=((b"allow", b"GET"),),
            )
            return

        path = scope.get("path")
        if not isinstance(path, str) or not _looks_like_position_history_route(path):
            await _send_error(
                send,
                status=404,
                error_code="route_not_found",
                message="Use /v1/tenants/{tenant_record_id}/positions/{position_record_id}/history.",
            )
            return

        try:
            request = _parse_position_history_request(path, scope.get("query_string", b""))
        except _InvalidHttpRequest:
            await _send_error(
                send,
                status=400,
                error_code="invalid_request",
                message="Correct the tenant/Position IDs and required known_at, purpose, and fields query parameters, then retry.",
            )
            return

        try:
            bearer_token = extract_bearer_token(_authorization_header(scope))
            principal = await self.authenticator.authenticate(bearer_token)
        except AuthenticationFailed:
            await _send_error(
                send,
                status=401,
                error_code="authentication_required",
                message="Provide one valid Bearer credential and retry.",
                extra_headers=((b"www-authenticate", b"Bearer"),),
            )
            return

        try:
            view = read_position_history(
                principal=principal,
                tenant_record_id=request.tenant_record_id,
                position_record_id=request.position_record_id,
                known_at=request.known_at,
                purpose_code=request.purpose_code,
                requested_fields=request.requested_fields,
                policy=self.policy,
                read_port=self.read_port,
            )
        except AuthorizationDeniedError:
            await _send_error(
                send,
                status=403,
                error_code="access_denied",
                message="Request only fields and a purpose authorized for this exact Position history.",
            )
            return
        except PositionHistoryIntegrityError:
            await _send_error(
                send,
                status=409,
                error_code="position_history_integrity_conflict",
                message="The Position history cannot be returned safely; ask an Orgmetra operator to inspect the authoritative lineage.",
            )
            return
        except Exception:  # noqa: BLE001 - HTTP boundary must fail closed without backend details.
            await _send_error(
                send,
                status=500,
                error_code="internal_error",
                message="Retry later or contact an Orgmetra operator with non-secret request metadata; never include the bearer token.",
            )
            return

        await _emit_json(
            send,
            status=200,
            payload={
                "resource_reference": view.resource_reference,
                "entries": [
                    {"fields": dict(entry.field_values)}
                    for entry in view.entries
                ],
            },
        )


def _looks_like_position_history_route(path: str) -> bool:
    """Recognize the versioned Position-history route before parsing IDs."""
    parts = path.strip("/").split("/")
    return (
        len(parts) == 6
        and tuple(parts[:2]) == _ROUTE_PREFIX
        and parts[3] == "positions"
        and parts[5] == "history"
    )


def _parse_position_history_request(path: str, raw_query: object) -> _ParsedPositionHistoryRequest:
    """Validate all caller-controlled path/query values before authentication."""
    parts = path.strip("/").split("/")
    try:
        tenant_record_id = UUID(parts[2])
        position_record_id = UUID(parts[4])
    except (ValueError, IndexError) as error:
        raise _InvalidHttpRequest("route IDs must be UUIDs") from error
    if tenant_record_id.int in (0, _MAX_UUID_INT) or position_record_id.int in (0, _MAX_UUID_INT):
        raise _InvalidHttpRequest("route IDs must be operational UUIDs")

    if not isinstance(raw_query, bytes):
        raise _InvalidHttpRequest("query_string must be bytes")
    try:
        query_text = raw_query.decode("ascii")
        pairs = parse_qsl(query_text, keep_blank_values=True, strict_parsing=True)
    except (UnicodeDecodeError, ValueError) as error:
        raise _InvalidHttpRequest("query string is malformed") from error

    query: dict[str, str] = {}
    for key, value in pairs:
        if key in query:
            raise _InvalidHttpRequest("duplicate query parameter")
        query[key] = value
    if frozenset(query) != _REQUIRED_QUERY_KEYS:
        raise _InvalidHttpRequest("query parameters are incomplete or unsupported")

    raw_known_at = query["known_at"]
    if _RFC3339_INSTANT_PATTERN.fullmatch(raw_known_at) is None:
        raise _InvalidHttpRequest("known_at must be a UTC RFC 3339 instant")
    try:
        known_at = datetime.fromisoformat(raw_known_at[:-1] + "+00:00")
    except ValueError as error:
        raise _InvalidHttpRequest("known_at must be a valid UTC RFC 3339 instant") from error
    purpose_code = query["purpose"]
    if _PURPOSE_PATTERN.fullmatch(purpose_code) is None:
        raise _InvalidHttpRequest("purpose must be a lower snake-case code")

    raw_fields = query["fields"].split(",")
    if any(_FIELD_PATTERN.fullmatch(field) is None for field in raw_fields):
        raise _InvalidHttpRequest("fields must be explicit lower snake-case names")
    if len(set(raw_fields)) != len(raw_fields):
        raise _InvalidHttpRequest("fields must not repeat")

    return _ParsedPositionHistoryRequest(
        tenant_record_id=tenant_record_id,
        position_record_id=position_record_id,
        known_at=known_at,
        purpose_code=purpose_code,
        requested_fields=frozenset(raw_fields),
    )
