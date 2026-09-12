"""Dependency-light ASGI boundary for governed Employment separation."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, timezone
import logging
import re
from secrets import token_urlsafe
from typing import Callable, Mapping
from uuid import UUID, uuid4

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
from orgmetra_people_api.mutation_http import _parse_command_headers, _send_error
from orgmetra_people_api.mutations import PeopleMutationNotFound
from orgmetra_people_api.separation import (
    EmploymentSeparationCommand,
    EmploymentSeparationIntegrityError,
    EmploymentSeparationPersistenceIntegrityError,
    EmploymentSeparationPort,
    separate_employment_record,
)

_LOGGER = logging.getLogger(__name__)
_ROUTE = "/v1/employment-separations"
_BODY_KEYS = frozenset(
    {
        "person_record_id",
        "employment_record_id",
        "expected_employment_record_version_id",
        "separation_effective_on",
        "separation_reason_code",
        "evidence_reference",
        "evidence_version_code",
        "confirmation_reference",
    }
)
_RFC3339_FULL_DATE = re.compile(r"\A\d{4}-\d{2}-\d{2}\Z", flags=re.ASCII)
_ACTOR_REFERENCE_PATTERN = re.compile(r"\A[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*\Z", flags=re.ASCII)
_MAX_UUID_INT = (1 << 128) - 1
_SUPPORT_REFERENCE_RANDOM_BYTES = 24


def _operational_uuid(field_name: str, value: object) -> UUID:
    """Parse one HTTP UUID while rejecting reserved sentinel identities."""
    if type(value) is not str:
        raise _InvalidHttpRequest(f"{field_name} must be a UUID string")
    try:
        parsed = UUID(value)
    except ValueError as error:
        raise _InvalidHttpRequest(f"{field_name} must be a UUID string") from error
    if parsed.int in (0, _MAX_UUID_INT):
        raise _InvalidHttpRequest(f"{field_name} must be an operational UUID")
    return parsed


def _generated_operational_uuid(field_name: str, id_factory: Callable[[], UUID]) -> UUID:
    """Treat malformed server-generated identities as operational failure, never caller error."""
    value = id_factory()
    if type(value) is not UUID or value.int in (0, _MAX_UUID_INT):
        raise RuntimeError(f"{field_name} factory did not return an operational UUID")
    return UUID(int=value.int)


def _business_date(value: object) -> date:
    """Parse the published full-date representation without datetime coercion."""
    if type(value) is not str or _RFC3339_FULL_DATE.fullmatch(value) is None:
        raise _InvalidHttpRequest("separation_effective_on must be an RFC 3339 full-date")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise _InvalidHttpRequest("separation_effective_on must be an RFC 3339 full-date") from error


def _command_from_payload(
    *,
    tenant_record_id: UUID,
    idempotency_key: str,
    payload: Mapping[str, object],
    audit_event_record_id: UUID,
    outbox_delivery_record_id: UUID,
) -> EmploymentSeparationCommand:
    """Build one exact separation command without admitting extra body fields."""
    if frozenset(payload) != _BODY_KEYS:
        raise _InvalidHttpRequest("separation body must contain exactly the published fields")
    return EmploymentSeparationCommand(
        tenant_record_id=tenant_record_id,
        person_record_id=_operational_uuid("person_record_id", payload["person_record_id"]),
        employment_record_id=_operational_uuid("employment_record_id", payload["employment_record_id"]),
        expected_employment_record_version_id=_operational_uuid(
            "expected_employment_record_version_id",
            payload["expected_employment_record_version_id"],
        ),
        separation_effective_on=_business_date(payload["separation_effective_on"]),
        separation_reason_code=payload["separation_reason_code"],  # type: ignore[arg-type]
        evidence_reference=payload["evidence_reference"],  # type: ignore[arg-type]
        evidence_version_code=payload["evidence_version_code"],  # type: ignore[arg-type]
        confirmation_reference=payload["confirmation_reference"],  # type: ignore[arg-type]
        idempotency_key=idempotency_key,
        audit_event_record_id=audit_event_record_id,
        outbox_delivery_record_id=outbox_delivery_record_id,
    )


@dataclass(frozen=True, slots=True)
class EmploymentSeparationAsgiApp:
    """Expose one purpose-bound buyer route for authoritative Employment separation."""

    authenticator: TokenAuthenticator
    policy: PurposeBoundAccessPolicy
    separation_port: EmploymentSeparationPort
    id_factory: Callable[[], UUID] = uuid4

    def __post_init__(self) -> None:
        """Reject incomplete dependency injection before serving high-impact writes."""
        if not isinstance(self.authenticator, TokenAuthenticator):
            raise TypeError("authenticator must implement TokenAuthenticator")
        if not isinstance(self.policy, PurposeBoundAccessPolicy):
            raise TypeError("policy must be a PurposeBoundAccessPolicy")
        if not isinstance(self.separation_port, EmploymentSeparationPort):
            raise TypeError("separation_port must implement EmploymentSeparationPort")
        if not callable(self.id_factory):
            raise TypeError("id_factory must be callable")

    async def __call__(self, scope: Mapping[str, object], receive: AsgiReceive, send: AsgiSend) -> None:
        """Serve one separation without leaking bearer tokens or database capabilities."""
        if scope.get("type") != "http":
            raise ValueError("EmploymentSeparationAsgiApp accepts only HTTP ASGI scopes")
        if scope.get("method") != "POST":
            await _send_error(
                send,
                status=405,
                payload={"error": "method_not_allowed", "message": "Use POST for Employment separation."},
                extra_headers=((b"allow", b"POST"),),
            )
            return
        if scope.get("path") != _ROUTE:
            await _send_error(
                send,
                status=404,
                payload={"error": "route_not_found", "message": f"Use {_ROUTE}."},
            )
            return

        try:
            headers = _parse_command_headers(scope)
            _require_json_content_type(scope)
            if _ACTOR_REFERENCE_PATTERN.fullmatch(headers.actor_reference) is None:
                raise _InvalidHttpRequest("X-Actor-Reference must be a namespaced opaque reference")
        except _UnsupportedMediaType:
            await _send_error(
                send,
                status=415,
                payload={"error": "unsupported_media_type", "message": "Send application/json and retry."},
            )
            return
        except (_InvalidHttpRequest, ValueError, TypeError):
            await _send_error(
                send,
                status=400,
                payload={"error": "invalid_request", "message": "Correct the command headers and retry."},
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
                payload={"error": "authentication_required", "message": "Provide one valid Bearer credential and retry."},
                extra_headers=((b"www-authenticate", b"Bearer"),),
            )
            return
        except Exception as error:  # noqa: BLE001 - identity backend failures must remain client-safe.
            support_reference = f"err_{token_urlsafe(_SUPPORT_REFERENCE_RANDOM_BYTES)}"
            _LOGGER.error(
                "Employment separation authentication failed",
                extra={
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
                    "message": "Retry later or contact an Orgmetra operator with the support reference.",
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
                payload={"error": "access_denied", "message": "Use the tenant and actor bound to the authenticated credential."},
            )
            return
        if headers.purpose_code != "workforce_admin":
            await _send_error(
                send,
                status=403,
                payload={"error": "access_denied", "message": "Employment separation requires workforce_admin purpose."},
            )
            return

        try:
            payload = await _read_json_object(receive)
        except _PayloadTooLarge:
            await _send_error(
                send,
                status=413,
                payload={"error": "payload_too_large", "message": "Send one bounded JSON separation command and retry."},
            )
            return
        except (_InvalidHttpRequest, ValueError, TypeError):
            await _send_error(
                send,
                status=400,
                payload={"error": "invalid_request", "message": "Correct the separation command and retry."},
            )
            return

        try:
            audit_event_record_id = _generated_operational_uuid("audit_event_record_id", self.id_factory)
            outbox_delivery_record_id = _generated_operational_uuid("outbox_delivery_record_id", self.id_factory)
        except Exception as error:  # noqa: BLE001 - server identity generation is an operational dependency.
            support_reference = f"err_{token_urlsafe(_SUPPORT_REFERENCE_RANDOM_BYTES)}"
            _LOGGER.error(
                "Employment separation server identity generation failed",
                extra={
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
                    "message": "Retry later or contact an Orgmetra operator with the support reference.",
                },
                support_reference=support_reference,
            )
            return

        try:
            command = _command_from_payload(
                tenant_record_id=headers.tenant_record_id,
                idempotency_key=headers.idempotency_key,
                payload=payload,
                audit_event_record_id=audit_event_record_id,
                outbox_delivery_record_id=outbox_delivery_record_id,
            )
        except (_InvalidHttpRequest, ValueError, TypeError):
            await _send_error(
                send,
                status=400,
                payload={"error": "invalid_request", "message": "Correct the separation command and retry."},
            )
            return

        try:
            result = await asyncio.to_thread(
                separate_employment_record,
                principal=principal,
                command=command,
                purpose_code=headers.purpose_code,
                policy=self.policy,
                separation_port=self.separation_port,
            )
        except AuthorizationDeniedError:
            await _send_error(
                send,
                status=403,
                payload={"error": "access_denied", "message": "Request the scope authorized for this exact Employment separation."},
            )
            return
        except PeopleMutationNotFound:
            await _send_error(
                send,
                status=404,
                payload={"error": "record_not_found", "message": "Verify the Person, Employment, and expected version, then retry."},
            )
            return
        except EmploymentSeparationPersistenceIntegrityError as error:
            support_reference = f"err_{token_urlsafe(_SUPPORT_REFERENCE_RANDOM_BYTES)}"
            _LOGGER.error(
                "Employment separation persistence integrity failed",
                extra={
                    "tenant_record_id": str(headers.tenant_record_id),
                    "employment_record_id": str(command.employment_record_id),
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
                    "message": "Retry later or contact an Orgmetra operator with the support reference.",
                },
                support_reference=support_reference,
            )
            return
        except EmploymentSeparationIntegrityError:
            await _send_error(
                send,
                status=409,
                payload={
                    "error": "separation_conflict",
                    "message": "Refresh Employment and Assignment state, confirm the evidence, and retry with a new key if semantics changed.",
                },
            )
            return
        except Exception as error:  # noqa: BLE001 - persistence details must never escape the HTTP boundary.
            support_reference = f"err_{token_urlsafe(_SUPPORT_REFERENCE_RANDOM_BYTES)}"
            _LOGGER.error(
                "Employment separation persistence failed",
                extra={
                    "tenant_record_id": str(headers.tenant_record_id),
                    "employment_record_id": str(command.employment_record_id),
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
                    "message": "Retry later or contact an Orgmetra operator with the support reference.",
                },
                support_reference=support_reference,
            )
            return

        recorded_at = result.recorded_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        await _send_json(
            send,
            status=200,
            payload={
                "employment_record_id": str(result.employment_record_id),
                "separated_employment_record_version_id": str(result.separated_employment_record_version_id),
                "recorded_at": recorded_at,
                "replayed": result.replayed,
            },
        )
