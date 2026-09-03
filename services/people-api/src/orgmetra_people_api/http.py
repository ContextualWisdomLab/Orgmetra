"""Dependency-light ASGI route for purpose-bound People reads.

The transport adapter owns HTTP parsing and stable, non-disclosing responses only.
Authentication, purpose-bound authorization, canonical HRIS retrieval, and tenant
isolation remain delegated to the existing People service contracts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
import logging
import re
from secrets import token_urlsafe
from typing import Awaitable, Callable, Mapping, Sequence
from urllib.parse import parse_qsl
from uuid import UUID

from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy

from orgmetra_people_api.auth import (
    AuthenticatedPrincipal,
    AuthenticationFailed,
    TokenAuthenticator,
    extract_bearer_token,
)
from orgmetra_people_api.people import (
    PeopleReadPort,
    PeopleRecordIntegrityError,
    PeopleRecordNotFound,
    read_worker_people_record,
)

AsgiReceive = Callable[[], Awaitable[dict[str, object]]]
AsgiSend = Callable[[dict[str, object]], Awaitable[None]]

_LOGGER = logging.getLogger(__name__)
_ROUTE_PREFIX = ("v1", "tenants")
_PURPOSE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_FIELD_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_RFC3339_FULL_DATE = re.compile(r"\A\d{4}-\d{2}-\d{2}\Z", flags=re.ASCII)
_MAX_UUID_INT = (1 << 128) - 1
_REQUIRED_QUERY_KEYS = frozenset({"effective_on", "purpose", "fields"})
_MAX_REQUEST_PATH_CHARACTERS = 256
_MAX_QUERY_STRING_BYTES = 4096
_MAX_QUERY_FIELDS = len(_REQUIRED_QUERY_KEYS) + 1
_MAX_REQUEST_HEADERS = 64
_MAX_REQUEST_HEADER_BYTES = 16384
_SUPPORT_REFERENCE_RANDOM_BYTES = 24


class _InvalidHttpRequest(ValueError):
    """Indicate malformed request input that must fail before authentication."""


@dataclass(frozen=True, slots=True)
class _ParsedWorkerRequest:
    """Validated, non-secret request attributes required by the People read use case."""

    tenant_record_id: UUID
    person_record_id: UUID
    effective_on: date
    purpose_code: str
    requested_fields: frozenset[str]


@dataclass(frozen=True, slots=True)
class PeopleAsgiApp:
    """Expose the governed worker read contract through one versioned ASGI route.

    Supported route::

        GET /v1/tenants/{tenant_record_id}/people/{person_record_id}
            ?effective_on=YYYY-MM-DD
            &purpose=people_read
            &fields=display_name,employment_status_code

    The app deliberately has no web-framework dependency. Deployments can mount it
    directly in an ASGI server or adapt it behind a gateway while preserving the
    same authentication/authorization and no-store response semantics.
    """

    authenticator: TokenAuthenticator
    policy: PurposeBoundAccessPolicy
    read_port: PeopleReadPort

    def __post_init__(self) -> None:
        """Reject incomplete dependency injection before serving protected data."""
        if not isinstance(self.authenticator, TokenAuthenticator):
            raise TypeError("authenticator must implement TokenAuthenticator")
        if not isinstance(self.policy, PurposeBoundAccessPolicy):
            raise TypeError("policy must be a PurposeBoundAccessPolicy")
        if not isinstance(self.read_port, PeopleReadPort):
            raise TypeError("read_port must implement PeopleReadPort")

    async def __call__(self, scope: Mapping[str, object], receive: AsgiReceive, send: AsgiSend) -> None:
        """Serve one HTTP request without exposing bearer tokens or internal errors."""
        del receive
        if scope.get("type") != "http":
            raise ValueError("PeopleAsgiApp accepts only HTTP ASGI scopes")

        method = scope.get("method")
        if method != "GET":
            await _send_json(
                send,
                status=405,
                payload={
                    "error": "method_not_allowed",
                    "message": "Use GET for the governed People read route.",
                },
                extra_headers=((b"allow", b"GET"),),
            )
            return

        path = scope.get("path")
        if not isinstance(path, str):
            await _send_json(
                send,
                status=404,
                payload={
                    "error": "route_not_found",
                    "message": "Use /v1/tenants/{tenant_record_id}/people/{person_record_id}.",
                },
            )
            return
        if len(path) > _MAX_REQUEST_PATH_CHARACTERS:
            await _send_json(
                send,
                status=400,
                payload={
                    "error": "invalid_request",
                    "message": "Use the canonical People route without oversized path data, then retry.",
                },
            )
            return
        if not _looks_like_people_route(path):
            await _send_json(
                send,
                status=404,
                payload={
                    "error": "route_not_found",
                    "message": "Use /v1/tenants/{tenant_record_id}/people/{person_record_id}.",
                },
            )
            return

        try:
            request = _parse_worker_request(path, scope.get("query_string", b""))
        except _InvalidHttpRequest:
            await _send_json(
                send,
                status=400,
                payload={
                    "error": "invalid_request",
                    "message": "Correct the tenant/person IDs and required effective_on, purpose, and fields query parameters, then retry.",
                },
            )
            return

        try:
            bearer_token = extract_bearer_token(_authorization_header(scope))
            principal = await self.authenticator.authenticate(bearer_token)
            if type(principal) is not AuthenticatedPrincipal:
                raise TypeError("authenticator returned an invalid principal")
        except AuthenticationFailed:
            await _send_json(
                send,
                status=401,
                payload={
                    "error": "authentication_required",
                    "message": "Provide one valid Bearer credential and retry.",
                },
                extra_headers=((b"www-authenticate", b"Bearer"),),
            )
            return
        except Exception as error:  # noqa: BLE001 - identity backend failures must remain client-safe.
            support_reference = f"err_{token_urlsafe(_SUPPORT_REFERENCE_RANDOM_BYTES)}"
            _LOGGER.error(
                "People read authentication backend failed",
                extra={
                    "route": "people",
                    "tenant_record_id": str(request.tenant_record_id),
                    "exception_type": type(error).__name__,
                    "support_reference": support_reference,
                },
            )
            await _send_json(
                send,
                status=500,
                payload={
                    "error": "internal_error",
                    "message": "Retry later or contact an Orgmetra operator with non-secret request metadata; never include the bearer token.",
                },
                support_reference=support_reference,
            )
            return

        try:
            view = read_worker_people_record(
                principal=principal,
                tenant_record_id=request.tenant_record_id,
                person_record_id=request.person_record_id,
                effective_on=request.effective_on,
                purpose_code=request.purpose_code,
                requested_fields=request.requested_fields,
                policy=self.policy,
                read_port=self.read_port,
            )
        except AuthorizationDeniedError:
            await _send_json(
                send,
                status=403,
                payload={
                    "error": "access_denied",
                    "message": "Request only fields and a purpose authorized for this exact worker record.",
                },
            )
            return
        except PeopleRecordNotFound:
            await _send_json(
                send,
                status=404,
                payload={
                    "error": "worker_not_found",
                    "message": "Verify the worker reference, tenant, and effective date, then retry.",
                },
            )
            return
        except PeopleRecordIntegrityError:
            await _send_json(
                send,
                status=409,
                payload={
                    "error": "worker_integrity_conflict",
                    "message": "The worker record cannot be returned safely; ask an Orgmetra operator to inspect the authoritative lineage.",
                },
            )
            return
        except Exception as error:  # noqa: BLE001 - HTTP boundary must fail closed without leaking backend details.
            support_reference = f"err_{token_urlsafe(_SUPPORT_REFERENCE_RANDOM_BYTES)}"
            _LOGGER.error(
                "People read persistence backend failed",
                extra={
                    "route": "people",
                    "tenant_record_id": str(request.tenant_record_id),
                    "exception_type": type(error).__name__,
                    "support_reference": support_reference,
                },
            )
            await _send_json(
                send,
                status=500,
                payload={
                    "error": "internal_error",
                    "message": "Retry later or contact an Orgmetra operator with non-secret request metadata; never include the bearer token.",
                },
                support_reference=support_reference,
            )
            return

        await _send_json(
            send,
            status=200,
            payload={
                "resource_reference": view.resource_reference,
                "fields": dict(view.field_values),
            },
        )


def _looks_like_people_route(path: str) -> bool:
    """Recognize only the versioned People route shape before parsing identifiers."""
    parts = path.strip("/").split("/")
    return len(parts) == 5 and tuple(parts[:2]) == _ROUTE_PREFIX and parts[3] == "people"


def _parse_worker_request(path: str, raw_query: object) -> _ParsedWorkerRequest:
    """Validate all caller-controlled path/query values before authentication."""
    parts = path.strip("/").split("/")
    try:
        tenant_record_id = UUID(parts[2])
        person_record_id = UUID(parts[4])
    except (ValueError, IndexError) as error:
        raise _InvalidHttpRequest("route IDs must be UUIDs") from error
    if tenant_record_id.int in (0, _MAX_UUID_INT) or person_record_id.int in (0, _MAX_UUID_INT):
        raise _InvalidHttpRequest("route IDs must be operational UUIDs")

    if not isinstance(raw_query, bytes):
        raise _InvalidHttpRequest("query_string must be bytes")
    if len(raw_query) > _MAX_QUERY_STRING_BYTES:
        raise _InvalidHttpRequest("query string exceeds the accepted size")
    try:
        query_text = raw_query.decode("ascii")
        pairs = parse_qsl(
            query_text,
            keep_blank_values=True,
            strict_parsing=True,
            max_num_fields=_MAX_QUERY_FIELDS,
        )
    except (UnicodeDecodeError, ValueError) as error:
        raise _InvalidHttpRequest("query string is malformed") from error

    query: dict[str, str] = {}
    for key, value in pairs:
        if key in query:
            raise _InvalidHttpRequest("duplicate query parameter")
        query[key] = value
    if frozenset(query) != _REQUIRED_QUERY_KEYS:
        raise _InvalidHttpRequest("query parameters are incomplete or unsupported")

    effective_on_raw = query["effective_on"]
    if _RFC3339_FULL_DATE.fullmatch(effective_on_raw) is None:
        raise _InvalidHttpRequest("effective_on must be an RFC 3339 full date")
    try:
        effective_on = date.fromisoformat(effective_on_raw)
    except ValueError as error:
        raise _InvalidHttpRequest("effective_on must be an ISO business date") from error

    purpose_code = query["purpose"]
    if _PURPOSE_PATTERN.fullmatch(purpose_code) is None:
        raise _InvalidHttpRequest("purpose must be a lower snake_case code")

    raw_fields = query["fields"].split(",")
    if any(_FIELD_PATTERN.fullmatch(field) is None for field in raw_fields):
        raise _InvalidHttpRequest("fields must be explicit lower snake_case names")
    if len(set(raw_fields)) != len(raw_fields):
        raise _InvalidHttpRequest("fields must not repeat")

    return _ParsedWorkerRequest(
        tenant_record_id=tenant_record_id,
        person_record_id=person_record_id,
        effective_on=effective_on,
        purpose_code=purpose_code,
        requested_fields=frozenset(raw_fields),
    )


def _authorization_header(scope: Mapping[str, object]) -> str | None:
    """Return one bounded ASCII Authorization header, rejecting malformed input."""
    raw_headers = scope.get("headers", ())
    if not isinstance(raw_headers, Sequence):
        raise AuthenticationFailed("request headers are invalid")
    if len(raw_headers) > _MAX_REQUEST_HEADERS:
        raise AuthenticationFailed("request headers exceed the accepted count")
    authorization_values: list[bytes] = []
    for header in raw_headers:
        if not isinstance(header, Sequence) or len(header) != 2:
            raise AuthenticationFailed("request headers are invalid")
        name, value = header
        if not isinstance(name, bytes) or not isinstance(value, bytes):
            raise AuthenticationFailed("request headers are invalid")
        if len(name) + len(value) > _MAX_REQUEST_HEADER_BYTES:
            raise AuthenticationFailed("request header exceeds the accepted size")
        if name.lower() == b"authorization":
            authorization_values.append(value)
    if len(authorization_values) != 1:
        raise AuthenticationFailed("exactly one authorization header is required")
    try:
        return authorization_values[0].decode("ascii")
    except UnicodeDecodeError as error:
        raise AuthenticationFailed("authorization header must be ASCII") from error


async def _send_json(
    send: AsgiSend,
    *,
    status: int,
    payload: Mapping[str, object],
    extra_headers: tuple[tuple[bytes, bytes], ...] = (),
    support_reference: str | None = None,
) -> None:
    """Emit deterministic no-store JSON and avoid relogging pre-enriched route failures."""
    response_payload = dict(payload)
    error_code = response_payload.get("error")
    route_failure_already_logged = (
        isinstance(error_code, str)
        and support_reference is not None
        and response_payload.get("error_code") == error_code
        and response_payload.get("next_action") == response_payload.get("message")
        and response_payload.get("support_reference") == support_reference
    )
    if isinstance(error_code, str):
        if support_reference is None:
            support_reference = f"err_{token_urlsafe(_SUPPORT_REFERENCE_RANDOM_BYTES)}"
        response_payload.update(
            {
                "error_code": error_code,
                "next_action": str(response_payload["message"]),
                "support_reference": support_reference,
            }
        )
        if not route_failure_already_logged:
            _LOGGER.info(
                "People read request rejected",
                extra={
                    "error_code": error_code,
                    "http_status": status,
                    "support_reference": support_reference,
                },
            )
    body = json.dumps(response_payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")
    headers = (
        (b"content-type", b"application/json"),
        (b"cache-control", b"no-store"),
        (b"vary", b"Authorization"),
        *extra_headers,
    )
    await send({"type": "http.response.start", "status": status, "headers": list(headers)})
    await send({"type": "http.response.body", "body": body, "more_body": False})
