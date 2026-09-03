"""Purpose-bound application contract for Assignment category corrections."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re
from typing import Protocol, runtime_checkable
from uuid import UUID

from orgmetra_keyverse_adapter import AuthorizationDecision, PurposeBoundAccessPolicy

from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.authorization import authorize_resource_fields

_MAX_UUID_INT = (1 << 128) - 1
_EXPLICIT_ASSIGNMENT_CATEGORY_CODES = frozenset({"primary", "concurrent_secondary"})
_CORRECTION_FIELDS = frozenset({"assignment_category_code"})
_REFERENCE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$")
_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_CONFIRMATION_REFERENCE_MAX = 300
_EVIDENCE_VERSION_MAX = 200
_IDEMPOTENCY_MIN = 16
_IDEMPOTENCY_MAX = 200


def _require_operational_uuid(field_name: str, value: object) -> UUID:
    """Require an exact operational UUID before any caller-defined behavior runs."""
    if type(value) is not UUID or value.int in (0, _MAX_UUID_INT):
        raise ValueError(f"{field_name} must be an operational UUID.")
    return value


def _require_reference(field_name: str, value: object) -> str:
    """Require one exact, bounded namespaced opaque reference."""
    if (
        type(value) is not str
        or not 1 <= len(value) <= _CONFIRMATION_REFERENCE_MAX
        or _REFERENCE_PATTERN.fullmatch(value) is None
    ):
        raise ValueError(f"{field_name} must be a namespaced opaque reference of at most 300 characters.")
    return value


def _require_version(value: object) -> str:
    """Require one exact, bounded whitespace-free evidence version token."""
    if (
        type(value) is not str
        or not 1 <= len(value) <= _EVIDENCE_VERSION_MAX
        or _VERSION_PATTERN.fullmatch(value) is None
    ):
        raise ValueError("evidence_version_code must be a whitespace-free version token of at most 200 characters.")
    return value


def _require_idempotency_key(value: object) -> str:
    """Require an exact visible-ASCII correction replay key."""
    if type(value) is not str or not (_IDEMPOTENCY_MIN <= len(value) <= _IDEMPOTENCY_MAX):
        raise ValueError("idempotency_key must be 16 to 200 visible ASCII characters.")
    if any(ord(character) < 0x21 or ord(character) > 0x7E for character in value):
        raise ValueError("idempotency_key must be 16 to 200 visible ASCII characters.")
    return value


@dataclass(frozen=True, slots=True)
class AssignmentCorrectionMutationCommand:
    """Human-confirmed command to replace one committed Assignment category fact."""

    tenant_record_id: UUID
    predecessor_assignment_record_id: UUID
    replacement_assignment_record_id: UUID
    assignment_supersession_record_id: UUID
    audit_event_record_id: UUID
    outbox_delivery_record_id: UUID
    corrected_category_code: str
    confirmation_reference: str
    evidence_version_code: str
    idempotency_key: str

    def __post_init__(self) -> None:
        """Fail closed before authorization or persistence on malformed evidence."""
        for field_name in (
            "tenant_record_id",
            "predecessor_assignment_record_id",
            "replacement_assignment_record_id",
            "assignment_supersession_record_id",
            "audit_event_record_id",
            "outbox_delivery_record_id",
        ):
            _require_operational_uuid(field_name, getattr(self, field_name))
        if self.predecessor_assignment_record_id == self.replacement_assignment_record_id:
            raise ValueError("replacement_assignment_record_id must differ from the predecessor.")
        if (
            type(self.corrected_category_code) is not str
            or self.corrected_category_code not in _EXPLICIT_ASSIGNMENT_CATEGORY_CODES
        ):
            raise ValueError("corrected_category_code must be primary or concurrent_secondary.")
        _require_reference("confirmation_reference", self.confirmation_reference)
        _require_version(self.evidence_version_code)
        _require_idempotency_key(self.idempotency_key)


@dataclass(frozen=True, slots=True)
class AssignmentCorrectionMutationResult:
    """Opaque replacement and provenance identities returned after commit."""

    replacement_assignment_record_id: UUID
    assignment_supersession_record_id: UUID

    def __post_init__(self) -> None:
        """Reject malformed adapter results at the service boundary."""
        _require_operational_uuid(
            "replacement_assignment_record_id",
            self.replacement_assignment_record_id,
        )
        _require_operational_uuid(
            "assignment_supersession_record_id",
            self.assignment_supersession_record_id,
        )


def assignment_correction_command_digest(
    *,
    command: AssignmentCorrectionMutationCommand,
    authorization: AuthorizationDecision,
) -> str:
    """Hash correction semantics while excluding retry-generated record identities."""
    if type(command) is not AssignmentCorrectionMutationCommand:
        raise TypeError("command must be an exact AssignmentCorrectionMutationCommand")
    if type(authorization) is not AuthorizationDecision:
        raise TypeError("authorization must be an exact AuthorizationDecision")
    payload = {
        "actor_reference": authorization.actor_reference,
        "command_route": "assignment-category-corrections",
        "method": "POST",
        "purpose_code": authorization.purpose_code,
        "semantic_command": {
            "confirmation_reference": command.confirmation_reference,
            "corrected_category_code": command.corrected_category_code,
            "evidence_version_code": command.evidence_version_code,
            "predecessor_assignment_record_id": str(command.predecessor_assignment_record_id),
        },
        "tenant_record_id": str(command.tenant_record_id),
    }
    return sha256(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")).hexdigest()


@runtime_checkable
class AssignmentCorrectionMutationPort(Protocol):
    """Persist one authorized category correction atomically inside Orgmetra."""

    def correct_assignment_category(
        self,
        *,
        command: AssignmentCorrectionMutationCommand,
        authorization: AuthorizationDecision,
    ) -> AssignmentCorrectionMutationResult:
        """Commit one linked correction or raise without partial writes."""


def correct_assignment_record_category(
    *,
    principal: AuthenticatedPrincipal,
    command: AssignmentCorrectionMutationCommand,
    purpose_code: str,
    policy: PurposeBoundAccessPolicy,
    mutation_port: AssignmentCorrectionMutationPort,
) -> AssignmentCorrectionMutationResult:
    """Authorize exactly one predecessor's category field before correction."""
    if type(command) is not AssignmentCorrectionMutationCommand:
        raise TypeError("command must be an exact AssignmentCorrectionMutationCommand")
    if not isinstance(mutation_port, AssignmentCorrectionMutationPort):
        raise TypeError("mutation_port must implement AssignmentCorrectionMutationPort")
    authorization = authorize_resource_fields(
        principal=principal,
        tenant_record_id=command.tenant_record_id,
        resource_tenant_record_id=command.tenant_record_id,
        resource_reference=f"assignment_record:{command.predecessor_assignment_record_id.hex}",
        purpose_code=purpose_code,
        operation_code="correct_record",
        resource_kind="assignment_record",
        requested_fields=_CORRECTION_FIELDS,
        policy=policy,
    )
    result = mutation_port.correct_assignment_category(
        command=command,
        authorization=authorization,
    )
    if type(result) is not AssignmentCorrectionMutationResult:
        raise TypeError("mutation_port must return an exact AssignmentCorrectionMutationResult")
    return result
