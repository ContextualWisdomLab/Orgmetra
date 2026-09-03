"""Purpose-bound ASGI boundary for immutable Assignment category correction."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from secrets import token_urlsafe
from typing import Callable, Mapping
from uuid import UUID, uuid4

from orgmetra_hris_kernel import KernelError
from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy

from orgmetra_people_api.assignment_correction_mutations import (
    AssignmentCorrectionMutationCommand,
    AssignmentCorrectionMutationPort,
    correct_assignment_record_category,
)
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
from orgmetra_people_api.mutations import PeopleMutationIntegrityError

_LOGGER = logging.getLogger(__name__)
_BODY_KEYS = frozenset(
    {
        "corrected_category_code",
        "confirmation_reference",
        "evidence_version_code",
    }
)
_MAX_UUID_INT = (1 << 128) - 1
_SUPPORT_REFERENCE_RANDOM_BYTES = 24


def _predecessor_from_path(path: object) -> UUID | None:
    """Return the operational predecessor identity for the one owned route."""
    if type(path) is not str:
        return None
    parts = path.strip("/").split("/")
    if len(parts) != 4 or parts[0] != "v1" or parts[1] != "assignment-records" or parts[3] != "category-corrections":
        return None
    try:
        predecessor = UUID(parts[2])
    except (AttributeError, ValueError):
        return None
    if predecessor.int in (0, _MAX_UUID_INT):
        return None
    return predecessor


def _require_body_string(payload: Mapping[str, object], field_name: str) -> str:
    """Require an exact JSON string and leave semantic validation to the command."""
    value = payload.get(field_name)
    if type(value) is not str:
        raise _InvalidHttpRequest(f"{field_name} must be a string")
    return value


def _correction_command(
    *,
    tenant_record_id: UUID,
    predecessor_assignment_record_id: UUID,
    payload: Mapping[str, object],
    idempotency_key: str,
    id_factory: Callable[[], UUID],
) -> AssignmentCorrectionMutationCommand:
    """Map one exact HTTP body onto the governed application command."""
    if frozenset(payload) != _BODY_KEYS:
        raise _InvalidHttpRequest("correction command fields are incomplete or unsupported")
    return AssignmentCorrectionMutationCommand(
        tenant_record_id=tenant_record_id,
        predecessor_assignment_record_id=predecessor_assignment_record_id,
        replacement_assignment_record_id=id_factory(),
        assignment_supersession_record_id=id_factory(),
        audit_event_record_id=id_factory(),
        outbox_delivery_record_id=id_factory(),
        corrected_category_code=_require_body_string(payload, "corrected_category_code"),
        confirmation_reference=_require_body_string(payload, "confirmation_reference"),
        evidence_version_code=_require_body_string(payload, "evidence_version_code"),
        idempotency_key=idempotency_key,
    )


@dataclass(frozen=True, slots=True)
class AssignmentCorrectionAsgiApp:
    """Expose one correction command without permitting in-place Assignment mutation.

    The route is ``POST /v1/assignment-records/{assignment_record_id}/category-corrections``.
    It authenticates the actor through Keyverse, binds tenant/actor/purpose/idempotency
    headers, authorizes only ``assignment_category_code`` for ``correct_record``, and
    returns opaque replacement plus supersession identities after the transaction commits.
    """

    authenticator: TokenAuthenticator
    correction_policy: PurposeBoundAccessPolicy
    mutation_port: AssignmentCorrectionMutationPort
    id_factory: Callable[[], UUID] = uuid4

    def __post_init__(self) -> None:
        """Reject incomplete governed dependencies before serving corrections."""
        if not isinstance(self.authenticator, TokenAuthenticator):
            raise TypeError("authenticator must implement TokenAuthenticator")
        if not isinstance(self.correction_policy, PurposeBoundAccessPolicy):
            raise TypeError("correction_policy must be a PurposeBoundAccessPolicy")
        if not isinstance(self.mutation_port, AssignmentCorrectionMutationPort):
            raise TypeError("mutation_port must implement AssignmentCorrectionMutationPort")
        if not callable(self.id_factory):
            raise TypeError("id_factory must be callable")

    async def __call__(self, scope: Mapping[str, object], receive: AsgiReceive, send: AsgiSend) -> None:
        """Serve one fail-closed correction without exposing credentials or free-text PII."""
        if scope.get("type") != "http":
            raise ValueError("AssignmentCorrectionAsgiApp accepts only HTTP ASGI scopes")
        if scope.get("method") != "POST":
            await _send_error(
                send,
                status=405,
                payload={"error": "method_not_allowed", "message": "Use POST for Assignment category corrections."},
                extra_headers=((b"allow", b"POST"),),
            )
            return

        predecessor = _predecessor_from_path(scope.get("path"))
        if predecessor is None:
            await _send_error(
                send,
                status=404,
                payload={
                    "error": "route_not_found",
                    "message": "Use /v1/assignment-records/{assignment_record_id}/category-corrections.",
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
                payload={"error": "unsupported_media_type", "message": "Send application/json and retry."},
            )
            return
        except (_InvalidHttpRequest, ValueError, TypeError):
            await _send_error(
                send,
                status=400,
                payload={"error": "invalid_request", "message": "Correct the governed command headers and retry."},
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
        except Exception as error:  # noqa: BLE001 - identity backend failures stay client-safe.
            support_reference = f"err_{token_urlsafe(_SUPPORT_REFERENCE_RANDOM_BYTES)}"
            _LOGGER.error(
                "Assignment correction authentication failed",
                extra={
                    "tenant_record_id": str(headers.tenant_record_id),
                    "predecessor_assignment_record_id": str(predecessor),
                    "exception_type": type(error).__name__,
                    "support_reference": support_reference,
                },
            )
            await _send_error(
                send,
                status=500,
                payload={
                    "error": "internal_error",
                    "message": "Retry later or contact an Orgmetra operator with the support reference; never include the bearer token.",
                },
                support_reference=support_reference,
            )
            return

        if principal.tenant_record_id != headers.tenant_record_id or principal.actor_reference != headers.actor_reference:
            await _send_error(
                send,
                status=403,
                payload={"error": "access_denied", "message": "Use the tenant and actor bound to the authenticated credential."},
            )
            return

        try:
            payload = await _read_json_object(receive)
            command = _correction_command(
                tenant_record_id=headers.tenant_record_id,
                predecessor_assignment_record_id=predecessor,
                payload=payload,
                idempotency_key=headers.idempotency_key,
                id_factory=self.id_factory,
            )
        except _PayloadTooLarge:
            await _send_error(
                send,
                status=413,
                payload={"error": "payload_too_large", "message": "Send one bounded JSON correction command and retry."},
            )
            return
        except (_InvalidHttpRequest, ValueError, TypeError, StopIteration):
            await _send_error(
                send,
                status=400,
                payload={"error": "invalid_request", "message": "Correct the category, confirmation, evidence version, and command fields, then retry."},
            )
            return

        try:
            result = correct_assignment_record_category(
                principal=principal,
                command=command,
                purpose_code=headers.purpose_code,
                policy=self.correction_policy,
                mutation_port=self.mutation_port,
            )
        except AuthorizationDeniedError:
            await _send_error(
                send,
                status=403,
                payload={"error": "access_denied", "message": "Request a purpose and scope authorized to correct only Assignment category."},
            )
            return
        except (PeopleMutationIntegrityError, KernelError):
            await _send_error(
                send,
                status=409,
                payload={
                    "error": "mutation_integrity_conflict",
                    "message": "The correction cannot be committed safely; refresh the Assignment and retry with current evidence.",
                },
            )
            return
        except Exception as error:  # noqa: BLE001 - persistence details must not cross the HTTP boundary.
            support_reference = f"err_{token_urlsafe(_SUPPORT_REFERENCE_RANDOM_BYTES)}"
            _LOGGER.error(
                "Assignment correction persistence failed",
                extra={
                    "tenant_record_id": str(headers.tenant_record_id),
                    "predecessor_assignment_record_id": str(predecessor),
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
                    "message": "Retry later or contact an Orgmetra operator with the support reference; never include the bearer token.",
                },
                support_reference=support_reference,
            )
            return

        replacement = str(result.replacement_assignment_record_id)
        await _send_json(
            send,
            status=201,
            payload={
                "replacement_assignment_record_id": replacement,
                "assignment_supersession_record_id": str(result.assignment_supersession_record_id),
            },
            extra_headers=((b"location", f"/v1/assignment-records/{replacement}".encode("ascii")),),
        )
