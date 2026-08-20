"""Dependency-light ASGI routes for governed People employment, position, and assignment writes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from hashlib import sha256
import json
import logging
import re
from secrets import token_urlsafe
from typing import Callable, Mapping, cast
from uuid import UUID, uuid4

from orgmetra_hris_kernel import KernelError
from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy

from orgmetra_people_api.auth import (
    AuthenticatedPrincipal,
    AuthenticationFailed,
    TokenAuthenticator,
    extract_bearer_token,
)
from orgmetra_people_api.hire_http import (
    _InvalidHttpRequest,
    _PayloadTooLarge,
    _UnsupportedMediaType,
    _read_json_object,
    _require_json_content_type,
)
from orgmetra_people_api.http import AsgiReceive, AsgiSend, _authorization_header, _send_json
from orgmetra_people_api.mutations import (
    AssignmentMutationCommand,
    EmploymentMutationCommand,
    PeopleMutationIntegrityError,
    PeopleMutationNotFound,
    PeopleMutationPort,
    PositionMutationCommand,
    create_assignment_record,
    create_employment_record,
    create_position_record,
    parse_allocation_ratio,
    validate_idempotency_key,
)

_LOGGER = logging.getLogger(__name__)
_RFC3339_FULL_DATE = re.compile(r"\A\d{4}-\d{2}-\d{2}\Z", flags=re.ASCII)
_PURPOSE_CODE_PATTERN = re.compile(r"\A[a-z][a-z0-9_]{2,63}\Z", flags=re.ASCII)
_MAX_UUID_INT = (1 << 128) - 1
_EMPLOYMENT_BODY_KEYS = frozenset(
    {
        "person_record_id",
        "employment_status_code",
        "employment_concurrency_code",
        "effective_from",
        "decision_reason",
        "confirmation_reference",
        "evidence_references",
    }
)
_POSITION_BODY_KEYS = frozenset(
    {
        "organization_unit_id",
        "job_profile_id",
        "position_status_code",
        "effective_from",
        "decision_reason",
        "confirmation_reference",
        "evidence_references",
    }
)
_ASSIGNMENT_BODY_KEYS = frozenset(
    {
        "employment_record_id",
        "person_record_id",
        "position_record_id",
        "allocation_ratio",
        "effective_from",
        "decision_reason",
        "confirmation_reference",
        "evidence_references",
    }
)
_EVIDENCE_REFERENCE_KEYS = frozenset({"evidence_reference", "evidence_version_code"})
_MAX_EVIDENCE_REFERENCES = 100
_MAX_EVIDENCE_REFERENCE_LENGTH = 500
_MAX_EVIDENCE_VERSION_LENGTH = 200
_MAX_DECISION_REASON_LENGTH = 4000
_MAX_CONFIRMATION_REFERENCE_LENGTH = 300
_MAX_ACTOR_REFERENCE_LENGTH = 200
_SUPPORT_REFERENCE_RANDOM_BYTES = 24


@dataclass(frozen=True, slots=True)
class _MutationHeaders:
    """Validated non-secret command headers required by the OpenAPI contract."""

    tenant_record_id: UUID
    actor_reference: str
    purpose_code: str
    idempotency_key: str


async def _send_error(
    send: AsgiSend,
    *,
    status: int,
    payload: Mapping[str, object],
    extra_headers: tuple[tuple[bytes, bytes], ...] = (),
    support_reference: str | None = None,
) -> None:
    """Normalize one internal error description to the published client-safe schema.

    A caller may supply an already-generated support reference so the restricted
    root-cause log and the buyer-visible error envelope share one lookup identity.
    """
    error_code = cast(str, payload["error"])
    message = cast(str, payload["message"])
    if support_reference is None:
        support_reference = f"err_{token_urlsafe(_SUPPORT_REFERENCE_RANDOM_BYTES)}"
    _LOGGER.info(
        "People mutation request rejected",
        extra={
            "error_code": error_code,
            "http_status": status,
            "support_reference": support_reference,
        },
    )
    await _send_json(
        send,
        status=status,
        payload={
            "error_code": error_code,
            "message": message,
            "next_action": message,
            "support_reference": support_reference,
        },
        extra_headers=extra_headers,
    )


@dataclass(frozen=True, slots=True)
class PeopleMutationAsgiApp:
    """Expose the three governed People mutation routes through one ASGI app.

    Supported routes::

        POST /v1/employment-records
        POST /v1/position-records
        POST /v1/assignment-records

    High-impact confirmation, versioned evidence, tenant/actor/purpose headers,
    and an idempotency key are required. Successful responses contain only the
    created opaque record identifier.
    """

    authenticator: TokenAuthenticator
    employment_policy: PurposeBoundAccessPolicy
    position_policy: PurposeBoundAccessPolicy
    assignment_policy: PurposeBoundAccessPolicy
    mutation_port: PeopleMutationPort
    id_factory: Callable[[], UUID] = uuid4

    def __post_init__(self) -> None:
        """Reject incomplete dependency injection before serving mutations."""
        if not isinstance(self.authenticator, TokenAuthenticator):
            raise TypeError("authenticator must implement TokenAuthenticator")
        if not isinstance(self.employment_policy, PurposeBoundAccessPolicy):
            raise TypeError("employment_policy must be a PurposeBoundAccessPolicy")
        if not isinstance(self.position_policy, PurposeBoundAccessPolicy):
            raise TypeError("position_policy must be a PurposeBoundAccessPolicy")
        if not isinstance(self.assignment_policy, PurposeBoundAccessPolicy):
            raise TypeError("assignment_policy must be a PurposeBoundAccessPolicy")
        if not isinstance(self.mutation_port, PeopleMutationPort):
            raise TypeError("mutation_port must implement PeopleMutationPort")
        if not callable(self.id_factory):
            raise TypeError("id_factory must be callable")

    async def __call__(self, scope: Mapping[str, object], receive: AsgiReceive, send: AsgiSend) -> None:
        """Serve one People mutation without exposing bearer tokens or backend secrets."""
        if scope.get("type") != "http":
            raise ValueError("PeopleMutationAsgiApp accepts only HTTP ASGI scopes")

        method = scope.get("method")
        if method != "POST":
            await _send_error(
                send,
                status=405,
                payload={
                    "error": "method_not_allowed",
                    "message": "Use POST for governed People mutation routes.",
                },
                extra_headers=((b"allow", b"POST"),),
            )
            return

        path = scope.get("path")
        route = _mutation_route(path)
        if route is None:
            await _send_error(
                send,
                status=404,
                payload={
                    "error": "route_not_found",
                    "message": "Use /v1/employment-records, /v1/position-records, or /v1/assignment-records.",
                },
            )
            return

        try:
            headers = _parse_command_headers(scope)
            _require_json_content_type(scope)
        except _UnsupportedMediaType:
            await _send_error(
                send,
                status=415,
                payload={
                    "error": "unsupported_media_type",
                    "message": "Send application/json and retry.",
                },
            )
            return
        except (_InvalidHttpRequest, ValueError, TypeError):
            await _send_error(
                send,
                status=400,
                payload={
                    "error": "invalid_request",
                    "message": "Correct the tenant, actor, purpose, confirmation, evidence, and command fields, then retry.",
                },
            )
            return

        try:
            bearer_token = extract_bearer_token(_authorization_header(scope))
            principal = await self.authenticator.authenticate(bearer_token)
            if not isinstance(principal, AuthenticatedPrincipal):
                raise TypeError("authenticator returned an invalid principal")
        except AuthenticationFailed:
            await _send_error(
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
                "People mutation authentication failed",
                extra={
                    "route": route,
                    "tenant_record_id": str(headers.tenant_record_id),
                    "exception_type": type(error).__name__,
                    "support_reference": support_reference,
                },
            )
            await _send_error(
                send,
                status=500,
                payload={
                    "error": "internal_error",
                    "message": "Retry later or contact an Orgmetra operator with non-sensitive request metadata; never include the bearer token.",
                },
                support_reference=support_reference,
            )
            return

        if (
            principal.tenant_record_id != headers.tenant_record_id
            or principal.actor_reference != headers.actor_reference
        ):
            await _send_error(
                send,
                status=403,
                payload={
                    "error": "access_denied",
                    "message": "Use the tenant and actor bound to the authenticated credential.",
                },
            )
            return

        try:
            payload = await _read_json_object(receive)
            command = _command_for_route(
                route,
                headers.tenant_record_id,
                payload,
                self.id_factory,
                headers.idempotency_key,
            )
        except _PayloadTooLarge:
            await _send_error(
                send,
                status=413,
                payload={
                    "error": "payload_too_large",
                    "message": "Send one bounded JSON mutation command and retry.",
                },
            )
            return
        except (_InvalidHttpRequest, ValueError, TypeError):
            await _send_error(
                send,
                status=400,
                payload={
                    "error": "invalid_request",
                    "message": "Correct the tenant, actor, purpose, confirmation, evidence, and command fields, then retry.",
                },
            )
            return

        try:
            created_id, location = _dispatch_mutation(
                route=route,
                principal=principal,
                command=command,
                purpose_code=headers.purpose_code,
                app=self,
            )
        except AuthorizationDeniedError:
            await _send_error(
                send,
                status=403,
                payload={
                    "error": "access_denied",
                    "message": "Request a purpose and scope authorized for this exact People mutation.",
                },
            )
            return
        except PeopleMutationNotFound:
            await _send_error(
                send,
                status=404,
                payload={
                    "error": "record_not_found",
                    "message": "Verify the parent organization, job, or worker references, then retry.",
                },
            )
            return
        except (PeopleMutationIntegrityError, KernelError):
            await _send_error(
                send,
                status=409,
                payload={
                    "error": "mutation_integrity_conflict",
                    "message": "The record cannot be saved safely; review overlapping employment, seat capacity, or conversion evidence.",
                },
            )
            return
        except Exception as error:  # noqa: BLE001 - HTTP boundary must fail closed without leaking backend details.
            support_reference = f"err_{token_urlsafe(_SUPPORT_REFERENCE_RANDOM_BYTES)}"
            _LOGGER.error(
                "People mutation persistence failed",
                extra={
                    "route": route,
                    "tenant_record_id": str(headers.tenant_record_id),
                    "correlation_reference": f"audit_event_record:{command.audit_event_record_id.hex}",
                    "exception_type": type(error).__name__,
                    "support_reference": support_reference,
                },
            )
            await _send_error(
                send,
                status=500,
                payload={
                    "error": "internal_error",
                    "message": "Retry later or contact an Orgmetra operator with non-sensitive request metadata; never include the bearer token.",
                },
                support_reference=support_reference,
            )
            return

        await _send_json(
            send,
            status=201,
            payload=created_id,
            extra_headers=((b"location", location.encode("ascii")),),
        )


def _mutation_route(path: object) -> str | None:
    """Return the canonical mutation leaf or None when the path is not owned here."""
    if not isinstance(path, str):
        return None
    parts = path.strip("/").split("/")
    if len(parts) != 2 or parts[0] != "v1":
        return None
    if parts[1] in {"employment-records", "position-records", "assignment-records"}:
        return parts[1]
    return None


def _parse_command_headers(scope: Mapping[str, object]) -> _MutationHeaders:
    """Validate OpenAPI command headers before authentication."""
    raw_headers = scope.get("headers", ())
    if not isinstance(raw_headers, (list, tuple)):
        raise _InvalidHttpRequest("command headers are invalid")
    values: dict[str, str] = {}
    for header in raw_headers:
        if not isinstance(header, (list, tuple)) or len(header) != 2:
            raise _InvalidHttpRequest("command headers are invalid")
        name, value = header
        if not isinstance(name, bytes) or not isinstance(value, bytes):
            raise _InvalidHttpRequest("command headers are invalid")
        key = name.lower().decode("ascii")
        if key in {
            "idempotency-key",
            "x-tenant-reference",
            "x-actor-reference",
            "x-purpose-code",
        }:
            if key in values:
                raise _InvalidHttpRequest("duplicate command header")
            try:
                values[key] = value.decode("ascii")
            except UnicodeDecodeError as error:
                raise _InvalidHttpRequest("command headers must be ASCII") from error
    required = {
        "idempotency-key",
        "x-tenant-reference",
        "x-actor-reference",
        "x-purpose-code",
    }
    if frozenset(values) < required:
        raise _InvalidHttpRequest("command headers are incomplete")
    try:
        idempotency_key = validate_idempotency_key(values["idempotency-key"])
    except ValueError as error:
        raise _InvalidHttpRequest("Idempotency-Key is invalid") from error
    try:
        tenant_record_id = UUID(values["x-tenant-reference"])
    except ValueError as error:
        raise _InvalidHttpRequest("X-Tenant-Reference must be a UUID") from error
    if tenant_record_id.int in (0, _MAX_UUID_INT):
        raise _InvalidHttpRequest("X-Tenant-Reference must be an operational UUID")
    actor_reference = values["x-actor-reference"]
    if not 1 <= len(actor_reference) <= _MAX_ACTOR_REFERENCE_LENGTH:
        raise _InvalidHttpRequest("X-Actor-Reference must contain 1 through 200 characters")
    purpose_code = values["x-purpose-code"]
    if _PURPOSE_CODE_PATTERN.fullmatch(purpose_code) is None:
        raise _InvalidHttpRequest("X-Purpose-Code must match the published lower-case purpose schema")
    return _MutationHeaders(
        tenant_record_id=tenant_record_id,
        actor_reference=actor_reference,
        purpose_code=purpose_code,
        idempotency_key=idempotency_key,
    )


def _evidence_version(payload: Mapping[str, object]) -> str:
    """Validate the exact OpenAPI evidence set and return its PII-minimized binding code."""
    raw_evidence = payload.get("evidence_references")
    if not isinstance(raw_evidence, list) or not 1 <= len(raw_evidence) <= _MAX_EVIDENCE_REFERENCES:
        raise _InvalidHttpRequest("evidence_references must contain 1 through 100 entries")

    normalized: list[tuple[str, str]] = []
    for reference in raw_evidence:
        if not isinstance(reference, Mapping) or frozenset(reference) != _EVIDENCE_REFERENCE_KEYS:
            raise _InvalidHttpRequest("each evidence reference must contain only reference and version")
        evidence_reference = reference["evidence_reference"]
        evidence_version = reference["evidence_version_code"]
        if (
            not isinstance(evidence_reference, str)
            or not 1 <= len(evidence_reference) <= _MAX_EVIDENCE_REFERENCE_LENGTH
        ):
            raise _InvalidHttpRequest("evidence_reference must be a bounded non-empty string")
        if not isinstance(evidence_version, str) or not 1 <= len(evidence_version) <= _MAX_EVIDENCE_VERSION_LENGTH:
            raise _InvalidHttpRequest("evidence_version_code must be a bounded non-empty string")
        normalized.append((evidence_reference, evidence_version))

    if len(set(normalized)) != len(normalized):
        raise _InvalidHttpRequest("evidence_references must be unique")
    canonical = json.dumps(sorted(normalized), ensure_ascii=False, separators=(",", ":"))
    return f"evidence_set_v1:{sha256(canonical.encode('utf-8')).hexdigest()}"


def _require_reason(payload: Mapping[str, object]) -> str:
    """Return a validated high-impact reason without copying the free text into audit metadata."""
    reason = payload.get("decision_reason")
    if (
        not isinstance(reason, str)
        or not reason.strip()
        or len(reason) > _MAX_DECISION_REASON_LENGTH
    ):
        raise _InvalidHttpRequest("decision_reason must be non-blank and at most 4000 characters")
    return reason


def _governance_evidence_binding(payload: Mapping[str, object]) -> str:
    """Bind decision reason and versioned evidence into one non-disclosing audit token."""
    canonical = json.dumps(
        {
            "decision_reason": _require_reason(payload),
            "evidence_set_version": _evidence_version(payload),
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"governance_evidence_v1:{sha256(canonical.encode('utf-8')).hexdigest()}"


def _require_string_field(payload: Mapping[str, object], field_name: str) -> str:
    """Require an exact JSON string instead of accepting values after coercion."""
    value = payload.get(field_name)
    if not isinstance(value, str):
        raise _InvalidHttpRequest(f"{field_name} must be a string")
    return value


def _parse_effective_date(payload: Mapping[str, object]) -> date:
    """Require the RFC 3339 full-date form published by the OpenAPI date contract."""
    value = _require_string_field(payload, "effective_from")
    if _RFC3339_FULL_DATE.fullmatch(value) is None:
        raise _InvalidHttpRequest("effective_from must be an RFC 3339 full-date")
    return date.fromisoformat(value)


def _require_confirmation_reference(payload: Mapping[str, object]) -> str:
    """Require the published bounded human-confirmation reference before domain parsing."""
    value = _require_string_field(payload, "confirmation_reference")
    if not 1 <= len(value) <= _MAX_CONFIRMATION_REFERENCE_LENGTH:
        raise _InvalidHttpRequest("confirmation_reference must contain 1 through 300 characters")
    return value


def _command_for_route(
    route: str,
    tenant_record_id: UUID,
    payload: Mapping[str, object],
    id_factory: Callable[[], UUID],
    idempotency_key: str,
) -> EmploymentMutationCommand | PositionMutationCommand | AssignmentMutationCommand:
    """Map one OpenAPI command body onto the matching application command."""
    evidence_version_code = _governance_evidence_binding(payload)
    confirmation_reference = _require_confirmation_reference(payload)
    effective_from = _parse_effective_date(payload)
    if route == "employment-records":
        if frozenset(payload) != _EMPLOYMENT_BODY_KEYS:
            raise _InvalidHttpRequest("employment command fields are incomplete or unsupported")
        return EmploymentMutationCommand(
            tenant_record_id=tenant_record_id,
            person_record_id=UUID(_require_string_field(payload, "person_record_id")),
            employment_record_id=id_factory(),
            employment_record_version_id=id_factory(),
            audit_event_record_id=id_factory(),
            outbox_delivery_record_id=id_factory(),
            employment_status_code=_require_string_field(payload, "employment_status_code"),
            employment_concurrency_code=_require_string_field(payload, "employment_concurrency_code"),
            effective_from=effective_from,
            confirmation_reference=confirmation_reference,
            evidence_version_code=evidence_version_code,
            idempotency_key=idempotency_key,
        )
    if route == "position-records":
        if frozenset(payload) != _POSITION_BODY_KEYS:
            raise _InvalidHttpRequest("position command fields are incomplete or unsupported")
        return PositionMutationCommand(
            tenant_record_id=tenant_record_id,
            organization_unit_id=UUID(_require_string_field(payload, "organization_unit_id")),
            job_profile_id=UUID(_require_string_field(payload, "job_profile_id")),
            position_record_id=id_factory(),
            position_record_version_id=id_factory(),
            audit_event_record_id=id_factory(),
            outbox_delivery_record_id=id_factory(),
            position_status_code=_require_string_field(payload, "position_status_code"),
            effective_from=effective_from,
            confirmation_reference=confirmation_reference,
            evidence_version_code=evidence_version_code,
            idempotency_key=idempotency_key,
        )
    if frozenset(payload) != _ASSIGNMENT_BODY_KEYS:
        raise _InvalidHttpRequest("assignment command fields are incomplete or unsupported")
    return AssignmentMutationCommand(
        tenant_record_id=tenant_record_id,
        employment_record_id=UUID(_require_string_field(payload, "employment_record_id")),
        person_record_id=UUID(_require_string_field(payload, "person_record_id")),
        position_record_id=UUID(_require_string_field(payload, "position_record_id")),
        assignment_record_id=id_factory(),
        audit_event_record_id=id_factory(),
        outbox_delivery_record_id=id_factory(),
        allocation_ratio=parse_allocation_ratio(payload["allocation_ratio"]),
        effective_from=effective_from,
        confirmation_reference=confirmation_reference,
        evidence_version_code=evidence_version_code,
        idempotency_key=idempotency_key,
    )


def _dispatch_mutation(
    *,
    route: str,
    principal: AuthenticatedPrincipal,
    command: EmploymentMutationCommand | PositionMutationCommand | AssignmentMutationCommand,
    purpose_code: str,
    app: PeopleMutationAsgiApp,
) -> tuple[dict[str, str], str]:
    """Invoke the authorized application function for the matched route."""
    if route == "employment-records":
        if not isinstance(command, EmploymentMutationCommand):
            raise TypeError("employment route requires EmploymentMutationCommand")
        result = create_employment_record(
            principal=principal,
            command=command,
            purpose_code=purpose_code,
            policy=app.employment_policy,
            mutation_port=app.mutation_port,
        )
        created = str(result.employment_record_id)
        return {"employment_record_id": created}, f"/v1/employment-records/{created}"
    if route == "position-records":
        if not isinstance(command, PositionMutationCommand):
            raise TypeError("position route requires PositionMutationCommand")
        result = create_position_record(
            principal=principal,
            command=command,
            purpose_code=purpose_code,
            policy=app.position_policy,
            mutation_port=app.mutation_port,
        )
        created = str(result.position_record_id)
        return {"position_record_id": created}, f"/v1/position-records/{created}"
    if not isinstance(command, AssignmentMutationCommand):
        raise TypeError("assignment route requires AssignmentMutationCommand")
    result = create_assignment_record(
        principal=principal,
        command=command,
        purpose_code=purpose_code,
        policy=app.assignment_policy,
        mutation_port=app.mutation_port,
    )
    created = str(result.assignment_record_id)
    return {"assignment_record_id": created}, f"/v1/assignment-records/{created}"