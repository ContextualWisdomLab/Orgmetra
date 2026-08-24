"""Governed vacancy-to-Assignment orchestration for authoritative People writes.

This module does not infer vacancy from UI state and does not create a second
staffing system of record.  It authorizes the exact Assignment target before a
protected vacancy resolver is allowed to inspect staffing truth, requires that
resolver to re-confirm the tenant/worker/Position/effective-date/evidence scope,
and then delegates to the existing authoritative Assignment mutation boundary.
The Assignment mutation performs its own authorization again immediately before
persistence, where existing atomic audit/outbox and seat-capacity rules remain
in force.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import re
from typing import Protocol, runtime_checkable
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.authorization import authorize_resource_fields
from orgmetra_people_api.mutations import (
    AssignmentMutationCommand,
    AssignmentMutationResult,
    PeopleMutationPort,
    create_assignment_record,
)

_MAX_UUID_INT = (1 << 128) - 1
_REFERENCE_PATTERN = re.compile(r"\A[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*\Z", flags=re.ASCII)
_VERSION_PATTERN = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._:-]*\Z", flags=re.ASCII)
_STAFFABLE_POSITION_STATUSES = frozenset({"active", "open"})
_ASSIGNMENT_FIELDS = frozenset({"assignment_record"})


class VacancyFillIntegrityError(RuntimeError):
    """Indicate that fresh authoritative vacancy evidence no longer matches the requested fill."""


def _validate_operational_uuid(field_name: str, value: object) -> None:
    """Require an exact UUID outside Orgmetra's reserved protocol sentinels."""
    if type(value) is not UUID or value.int in (0, _MAX_UUID_INT):
        raise ValueError(f"{field_name} must be an operational UUID.")


def _validate_reference(field_name: str, value: object) -> None:
    """Require one exact built-in, namespaced opaque evidence reference."""
    if type(value) is not str or _REFERENCE_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a namespaced opaque reference.")


def _validate_version(value: object) -> None:
    """Require one exact built-in evidence-version token."""
    if type(value) is not str or _VERSION_PATTERN.fullmatch(value) is None:
        raise ValueError("evidence_version_code must be a whitespace-free version token.")


@dataclass(frozen=True, slots=True, repr=False)
class VacancyFillVerification:
    """Value-minimized human-confirmed staffing truth returned by an authoritative resolver.

    The verification deliberately carries no employee name, compensation,
    assessment result, free-form review text, or model output.  It proves only
    the exact correlation needed to decide whether the requested Assignment can
    still consume the reviewed vacancy at one business-effective date.
    """

    tenant_record_id: UUID
    employment_record_id: UUID
    person_record_id: UUID
    position_record_id: UUID
    effective_on: date
    position_status_code: str
    available_allocation_ratio: Decimal
    confirmation_reference: str
    evidence_version_code: str
    review_state: str = "human_confirmed"

    def __post_init__(self) -> None:
        """Fail closed on malformed or non-human vacancy evidence before mutation."""
        for field_name in (
            "tenant_record_id",
            "employment_record_id",
            "person_record_id",
            "position_record_id",
        ):
            _validate_operational_uuid(field_name, getattr(self, field_name))
        if type(self.effective_on) is not date:
            raise ValueError("effective_on must be a business date.")
        if type(self.position_status_code) is not str or self.position_status_code not in _STAFFABLE_POSITION_STATUSES:
            raise ValueError("position_status_code must be active or open.")
        if type(self.available_allocation_ratio) is not Decimal or not self.available_allocation_ratio.is_finite():
            raise ValueError("available_allocation_ratio must be a finite Decimal.")
        if self.available_allocation_ratio <= Decimal("0") or self.available_allocation_ratio > Decimal("1.0000"):
            raise ValueError("available_allocation_ratio must be greater than 0 and at most 1.0000.")
        if self.available_allocation_ratio.as_tuple().exponent < -4:
            raise ValueError("available_allocation_ratio must have at most four decimal places.")
        _validate_reference("confirmation_reference", self.confirmation_reference)
        _validate_version(self.evidence_version_code)
        if type(self.review_state) is not str or self.review_state != "human_confirmed":
            raise ValueError("review_state must be human_confirmed.")

    def __repr__(self) -> str:
        """Avoid leaking correlation identifiers through routine logs and assertion output."""
        return "VacancyFillVerification(<redacted>)"


@runtime_checkable
class VacancyFillAuthority(Protocol):
    """Re-resolve authoritative bitemporal staffing truth for one proposed Assignment."""

    def verify_vacancy_fill(self, *, command: AssignmentMutationCommand) -> VacancyFillVerification:
        """Return fresh human-confirmed vacancy evidence or raise without side effects."""


def _validate_command_runtime(command: AssignmentMutationCommand) -> None:
    """Reject caller-defined runtime primitives before authorization or protected resolution."""
    for field_name in (
        "tenant_record_id",
        "employment_record_id",
        "person_record_id",
        "position_record_id",
        "assignment_record_id",
        "audit_event_record_id",
        "outbox_delivery_record_id",
    ):
        _validate_operational_uuid(field_name, getattr(command, field_name))
    if type(command.effective_from) is not date or type(command.allocation_ratio) is not Decimal:
        raise TypeError("AssignmentMutationCommand trust-bearing fields must use exact runtime primitives")
    for value in (command.confirmation_reference, command.evidence_version_code, command.idempotency_key):
        if type(value) is not str:
            raise TypeError("AssignmentMutationCommand trust-bearing fields must use exact runtime primitives")


def _require_matching_verification(
    *, command: AssignmentMutationCommand, verification: VacancyFillVerification
) -> None:
    """Require fresh resolver evidence to match the exact proposed Assignment and its review."""
    if (
        verification.tenant_record_id != command.tenant_record_id
        or verification.employment_record_id != command.employment_record_id
        or verification.person_record_id != command.person_record_id
        or verification.position_record_id != command.position_record_id
        or verification.effective_on != command.effective_from
        or verification.confirmation_reference != command.confirmation_reference
        or verification.evidence_version_code != command.evidence_version_code
        or verification.available_allocation_ratio < command.allocation_ratio
    ):
        raise VacancyFillIntegrityError("authoritative vacancy evidence no longer matches the proposed Assignment")


def fill_position_vacancy(
    *,
    principal: AuthenticatedPrincipal,
    command: AssignmentMutationCommand,
    purpose_code: str,
    policy: PurposeBoundAccessPolicy,
    vacancy_authority: VacancyFillAuthority,
    mutation_port: PeopleMutationPort,
) -> AssignmentMutationResult:
    """Fill one reviewed vacancy through the authoritative Assignment mutation boundary.

    Authorization occurs twice by design.  The first decision gates access to
    protected staffing truth; after fresh vacancy verification, the existing
    Assignment command path independently authorizes again immediately before
    the mutation port can persist authoritative HRIS truth and audit/outbox
    evidence.  A vacancy verification is therefore evidence, never mutation
    authority by itself.
    """
    if type(command) is not AssignmentMutationCommand:
        raise TypeError("command must be an exact AssignmentMutationCommand")
    _validate_command_runtime(command)
    if type(purpose_code) is not str:
        raise TypeError("purpose_code must be an exact string")
    if not isinstance(vacancy_authority, VacancyFillAuthority):
        raise TypeError("vacancy_authority must implement VacancyFillAuthority")
    if not isinstance(mutation_port, PeopleMutationPort):
        raise TypeError("mutation_port must implement PeopleMutationPort")

    authorize_resource_fields(
        principal=principal,
        tenant_record_id=command.tenant_record_id,
        resource_tenant_record_id=command.tenant_record_id,
        resource_reference=f"assignment_record:{command.assignment_record_id.hex}",
        purpose_code=purpose_code,
        operation_code="create_record",
        resource_kind="assignment_record",
        requested_fields=_ASSIGNMENT_FIELDS,
        policy=policy,
    )

    fresh_verification = vacancy_authority.verify_vacancy_fill(command=command)
    if type(fresh_verification) is not VacancyFillVerification:
        raise TypeError("vacancy_authority must return an exact VacancyFillVerification")
    _require_matching_verification(command=command, verification=fresh_verification)

    return create_assignment_record(
        principal=principal,
        command=command,
        purpose_code=purpose_code,
        policy=policy,
        mutation_port=mutation_port,
    )
