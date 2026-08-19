"""Dependency-light ASGI route for governed hire-to-worker materialization.

The transport adapter owns HTTP parsing and stable, non-disclosing responses.
Authorization, conversion persistence, and audit/outbox insertion remain in the
existing hire-acceptance contracts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
import logging
import re
from typing import Mapping
from urllib.parse import parse_qsl
from uuid import UUID

from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy

from orgmetra_people_api.auth import AuthenticationFailed, TokenAuthenticator, extract_bearer_token
from orgmetra_people_api.hire import (
    HireAcceptanceCommand,
    HireAcceptancePort,
    HireDecisionIntegrityError,
    HireDecisionNotFound,
    accept_confirmed_hire,
)
from orgmetra_people_api.http import (
    AsgiReceive,
    AsgiSend,
    _authorization_header,
    _send_json,
)
from orgmetra_people_api.mutations import validate_idempotency_key

_LOGGER = logging.getLogger(__name__)
_ROUTE_PREFIX = ("v1", "tenants")
_ROUTE_LEAF = "candidate-worker-conversions"
_PURPOSE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_MAX_UUID_INT = (1 << 128) - 1
_MAX_BODY_BYTES = 65536
_REQUIRED_BODY_KEYS = frozenset(
    {
        "candidate_profile_id",
        "selection_decision_id",
        "person_record_id",
        "person_name_record_id",
        "employment_record_id",
        "employment_record_version_id",
        "candidate_worker_conversion_record_id",
        "audit_event_record_id",
        "outbox_delivery_record_id",
        "effective_from",
        "display_name",
        "employment_status_code",
    }
)


class _InvalidHttpRequest(ValueError):
    """Indicate malformed hire input that must fail closed."""


class _PayloadTooLarge(ValueError):
    """Indicate a request body that exceeds the bounded hire command contract."""


class _UnsupportedMediaType(ValueError):
    """Indicate a missing or non-JSON content type."""


@dataclass(frozen=True, slots=True)
class HireAcceptanceAsgiApp:
    """Expose confirmed-hire materialization through one versioned ASGI route.

    Supported route::

        POST /v1/tenants/{tenant_record_id}/candidate-worker-conversions
            ?purpose=candidate_hire

    Successful responses contain only opaque worker identities. Display names and
    other necessary PII stay inside the authoritative write and never appear in
    the HTTP body.
    """

    authenticator: TokenAuthenticator
    policy: PurposeBoundAccessPolicy
    mutation_port: HireAcceptancePort

    def __post_init__(self) -> None:
        """Reject incomplete dependency injection before serving mutations."""
        if not isinstance(self.authenticator, TokenAuthenticator):
            raise TypeError("authenticator must implement TokenAuthenticator")
        if not isinstance(self.policy, PurposeBoundAccessPolicy):
            raise TypeError("policy must be a PurposeBoundAccessPolicy")
        if not isinstance(self.mutation_port, HireAcceptancePort):
            raise TypeError("mutation_port must implement HireAcceptancePort")

    async def __call__(self, scope: Mapping[str, object], receive: AsgiReceive, send: AsgiSend) -> None:
        """Serve one hire mutation without exposing bearer tokens or backend secrets."""
        if scope.get("type") != "http":
            raise ValueError("HireAcceptanceAsgiApp accepts only HTTP ASGI scopes")

        method = scope.get("method")
        if method != "POST":
            await _send_json(
                send,
                status=405,
                payload={
                    "error": "method_not_allowed",
                    "message": "Use POST for the governed hire acceptance route.",
                },
                extra_headers=((b"allow", b"POST"),),
            )
            return

        path = scope.get("path")
        if not isinstance(path, str) or not _looks_like_hire_route(path):
            await _send_json(
                send,
                status=404,
                payload={
                    "error": "route_not_found",
                    "message": "Use /v1/tenants/{tenant_record_id}/candidate-worker-conversions.",
                },
            )
            return

        try:
            tenant_record_id, purpose_code = _parse_hire_route(path, scope.get("query_string", b""))
        except (_InvalidHttpRequest, ValueError, TypeError):
            await _send_json(
                send,
                status=400,
                payload={
                    "error": "invalid_request",
                    "message": "Correct the tenant and purpose fields, then retry.",
                },
            )
            return

        try:
            bearer_token = extract_bearer_token(_authorization_header(scope))
            principal = await self.authenticator.authenticate(bearer_token)
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

        if principal.tenant_record_id != tenant_record_id:
            await _send_json(
                send,
                status=403,
                payload={
                    "error": "access_denied",
                    "message": "Use the tenant bound to the authenticated credential.",
                },
            )
            return

        try:
            idempotency_key = _parse_idempotency_key(scope)
            _require_json_content_type(scope)
            payload = await _read_json_object(receive)
            command = _command_from_payload(tenant_record_id, payload, idempotency_key)
        except _PayloadTooLarge:
            await _send_json(
                send,
                status=413,
                payload={
                    "error": "payload_too_large",
                    "message": "Send one bounded JSON hire command and retry.",
                },
            )
            return
        except _UnsupportedMediaType:
            await _send_json(
                send,
                status=415,
                payload={
                    "error": "unsupported_media_type",
                    "message": "Send application/json and retry.",
                },
            )
            return
        except (_InvalidHttpRequest, ValueError, TypeError):
            await _send_json(
                send,
                status=400,
                payload={
                    "error": "invalid_request",
                    "message": "Correct the idempotency key and hire command fields, then retry.",
                },
            )
            return

        try:
            result = accept_confirmed_hire(
                principal=principal,
                command=command,
                purpose_code=purpose_code,
                policy=self.policy,
                mutation_port=self.mutation_port,
            )
        except AuthorizationDeniedError:
            await _send_json(
                send,
                status=403,
                payload={
                    "error": "access_denied",
                    "message": "Request a purpose and scope authorized for this exact confirmed hire decision.",
                },
            )
            return
        except HireDecisionNotFound:
            await _send_json(
                send,
                status=404,
                payload={
                    "error": "hire_decision_not_found",
                    "message": "Verify the confirmed hire decision, tenant, and sealed evidence, then retry.",
                },
            )
            return
        except HireDecisionIntegrityError:
            await _send_json(
                send,
                status=409,
                payload={
                    "error": "hire_integrity_conflict",
                    "message": "The hire cannot be materialized safely; ask an Orgmetra operator to inspect the decision lineage.",
                },
            )
            return
        except Exception as error:  # noqa: BLE001 - HTTP boundary must fail closed without leaking backend details.
            _LOGGER.error(
                "Hire materialization persistence failed",
                extra={
                    "route": _ROUTE_LEAF,
                    "tenant_record_id": str(tenant_record_id),
                    "correlation_reference": f"audit_event_record:{command.audit_event_record_id.hex}",
                    "exception_type": type(error).__name__,
                },
            )
            await _send_json(
                send,
                status=500,
                payload={
                    "error": "internal_error",
                    "message": "Retry later or contact an Orgmetra operator with non-sensitive request metadata; never include the bearer token.",
                },
            )
            return

        await _send_json(
            send,
            status=201,
            payload={
                "candidate_worker_conversion_record_id": str(result.candidate_worker_conversion_record_id),
                "employment_record_id": str(result.employment_record_id),
                "person_record_id": str(result.person_record_id),
            },
        )


def _looks_like_hire_route(path: str) -> bool:
    """Recognize only the versioned hire-acceptance route shape."""
    parts = path.strip("/").split("/")
    return len(parts) == 4 and tuple(parts[:2]) == _ROUTE_PREFIX and parts[3] == _ROUTE_LEAF


def _parse_hire_route(path: str, raw_query: object) -> tuple[UUID, str]:
    """Validate tenant and purpose before authentication and body interpretation."""
    parts = path.strip("/").split("/")
    try:
        tenant_record_id = UUID(parts[2])
    except (ValueError, IndexError) as error:
        raise _InvalidHttpRequest("tenant_record_id must be a UUID") from error
    if tenant_record_id.int in (0, _MAX_UUID_INT):
        raise _InvalidHttpRequest("tenant_record_id must be an operational UUID")

    if not isinstance(raw_query, bytes):
        raise _InvalidHttpRequest("query_string must be bytes")
    try:
        query_text = raw_query.decode("ascii")
        pairs = parse_qsl(
            query_text,
            keep_blank_values=True,
            strict_parsing=True,
        )
    except (UnicodeDecodeError, ValueError) as error:
        raise _InvalidHttpRequest("query string is malformed") from error

    query: dict[str, str] = {}
    for key, value in pairs:
        if key in query:
            raise _InvalidHttpRequest("duplicate query parameter")
        query[key] = value
    if frozenset(query) != frozenset({"purpose"}):
        raise _InvalidHttpRequest("purpose query parameter is required")
    purpose_code = query["purpose"]
    if _PURPOSE_PATTERN.fullmatch(purpose_code) is None:
        raise _InvalidHttpRequest("purpose must be a lower snake_case code")
    return tenant_record_id, purpose_code


def _parse_idempotency_key(scope: Mapping[str, object]) -> str:
    """Require exactly one visible-ASCII Idempotency-Key after authentication."""
    raw_headers = scope.get("headers", ())
    if not isinstance(raw_headers, (list, tuple)):
        raise _InvalidHttpRequest("Idempotency-Key is required")
    values: list[bytes] = []
    for header in raw_headers:
        if not isinstance(header, (list, tuple)) or len(header) != 2:
            raise _InvalidHttpRequest("Idempotency-Key is required")
        name, value = header
        if not isinstance(name, bytes) or not isinstance(value, bytes):
            raise _InvalidHttpRequest("Idempotency-Key is required")
        if name.lower() == b"idempotency-key":
            values.append(value)
    if len(values) != 1:
        raise _InvalidHttpRequest("exactly one Idempotency-Key is required")
    try:
        decoded = values[0].decode("ascii")
        return validate_idempotency_key(decoded)
    except (UnicodeDecodeError, ValueError) as error:
        raise _InvalidHttpRequest("Idempotency-Key is invalid") from error


def _require_json_content_type(scope: Mapping[str, object]) -> None:
    """Accept exactly one application/json content type before reading the body."""
    raw_headers = scope.get("headers", ())
    if not isinstance(raw_headers, (list, tuple)):
        raise _UnsupportedMediaType("content-type is required")
    values: list[bytes] = []
    for header in raw_headers:
        if not isinstance(header, (list, tuple)) or len(header) != 2:
            raise _UnsupportedMediaType("content-type is required")
        name, value = header
        if not isinstance(name, bytes) or not isinstance(value, bytes):
            raise _UnsupportedMediaType("content-type is required")
        if name.lower() == b"content-type":
            values.append(value)
    if len(values) != 1 or values[0].split(b";", 1)[0].strip().lower() != b"application/json":
        raise _UnsupportedMediaType("application/json is required")


async def _read_json_object(receive: AsgiReceive) -> dict[str, object]:
    """Read one bounded JSON object across ordinary ASGI request-body frames."""
    body = bytearray()
    while True:
        message = await receive()
        if message.get("type") != "http.request":
            raise _InvalidHttpRequest("request body is missing")
        raw_chunk = message.get("body", b"")
        if not isinstance(raw_chunk, (bytes, bytearray)):
            raise _InvalidHttpRequest("request body must be bytes")
        if len(body) + len(raw_chunk) > _MAX_BODY_BYTES:
            raise _PayloadTooLarge("hire command exceeds the bounded size")
        body.extend(raw_chunk)
        if message.get("more_body") is not True:
            break
    if len(body) == 0:
        raise _InvalidHttpRequest("request body is empty")
    try:
        payload = json.loads(bytes(body), object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise _InvalidHttpRequest("request body must be one JSON object") from error
    if not isinstance(payload, dict):
        raise _InvalidHttpRequest("request body must be one JSON object")
    return payload


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Fail closed when a JSON object repeats a member name."""
    payload: dict[str, object] = {}
    for key, value in pairs:
        if key in payload:
            raise _InvalidHttpRequest("duplicate JSON member")
        payload[key] = value
    return payload


def _command_from_payload(
    tenant_record_id: UUID,
    payload: Mapping[str, object],
    idempotency_key: str,
) -> HireAcceptanceCommand:
    """Map one exact JSON object and validated idempotency key onto the hire command."""
    if frozenset(payload) != _REQUIRED_BODY_KEYS:
        raise _InvalidHttpRequest("hire command fields are incomplete or unsupported")
    try:
        effective_from = date.fromisoformat(str(payload["effective_from"]))
        return HireAcceptanceCommand(
            tenant_record_id=tenant_record_id,
            candidate_profile_id=UUID(str(payload["candidate_profile_id"])),
            selection_decision_id=UUID(str(payload["selection_decision_id"])),
            person_record_id=UUID(str(payload["person_record_id"])),
            person_name_record_id=UUID(str(payload["person_name_record_id"])),
            employment_record_id=UUID(str(payload["employment_record_id"])),
            employment_record_version_id=UUID(str(payload["employment_record_version_id"])),
            candidate_worker_conversion_record_id=UUID(
                str(payload["candidate_worker_conversion_record_id"])
            ),
            audit_event_record_id=UUID(str(payload["audit_event_record_id"])),
            outbox_delivery_record_id=UUID(str(payload["outbox_delivery_record_id"])),
            effective_from=effective_from,
            display_name=payload["display_name"],  # type: ignore[arg-type]
            idempotency_key=idempotency_key,
            employment_status_code=payload["employment_status_code"],  # type: ignore[arg-type]
        )
    except (TypeError, ValueError) as error:
        raise _InvalidHttpRequest("hire command fields are invalid") from error
