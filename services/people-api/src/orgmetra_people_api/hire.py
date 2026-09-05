"""Governed application contract for materializing a confirmed hire.

The application layer authorizes the exact immutable selection decision before
crossing the mutation port. The port then owns one tenant-scoped transaction
that materializes authoritative Person/Employment facts together with the
candidate-to-worker conversion and its immutable audit/outbox evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
import re
from typing import Protocol, runtime_checkable
from uuid import UUID

from orgmetra_keyverse_adapter import AuthorizationDecision, PurposeBoundAccessPolicy

from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.authorization import authorize_resource_fields
from orgmetra_people_api.mutations import validate_idempotency_key

_MAX_UUID_INT = (1 << 128) - 1
_STATUS_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_MAX_DISPLAY_NAME_LENGTH = 512
_HIRE_MUTATION_FIELDS = frozenset({"candidate_worker_conversion"})


class HireDecisionNotFound(LookupError):
    """Indicate that no exact confirmed decision can authorize the hire mutation."""


class HireDecisionIntegrityError(RuntimeError):
    """Indicate that decision provenance cannot safely materialize worker truth."""


def _validate_operational_uuid(field_name: str, value: object) -> None:
    """Require an exact UUID outside Orgmetra's reserved protocol sentinels."""
    if type(value) is not UUID or value.int in (0, _MAX_UUID_INT):
        raise ValueError(f"{field_name} must be an operational UUID.")


@dataclass(frozen=True, slots=True)
class HireAcceptanceCommand:
    """Opaque identities and business facts needed to materialize one confirmed hire.

    All identifiers are supplied explicitly so retries and upstream idempotency
    controls can address the same intended records rather than silently minting
    a second worker lineage. ``display_name`` is necessary PII and remains only
    inside the authoritative Person record; the audit/outbox envelope stores no
    copy of that value.
    """

    tenant_record_id: UUID
    candidate_profile_id: UUID
    selection_decision_id: UUID
    person_record_id: UUID
    person_name_record_id: UUID
    employment_record_id: UUID
    employment_record_version_id: UUID
    candidate_worker_conversion_record_id: UUID
    audit_event_record_id: UUID
    outbox_delivery_record_id: UUID
    effective_from: date
    display_name: str
    idempotency_key: str
    employment_status_code: str = "active"

    def __post_init__(self) -> None:
        """Fail closed before authorization or persistence on malformed input."""
        for field_name in (
            "tenant_record_id",
            "candidate_profile_id",
            "selection_decision_id",
            "person_record_id",
            "person_name_record_id",
            "employment_record_id",
            "employment_record_version_id",
            "candidate_worker_conversion_record_id",
            "audit_event_record_id",
            "outbox_delivery_record_id",
        ):
            _validate_operational_uuid(field_name, getattr(self, field_name))
        if type(self.effective_from) is not date:
            raise ValueError("effective_from must be a business date.")
        if type(self.display_name) is not str:
            raise ValueError("display_name must be a string.")
        try:
            self.display_name.encode("utf-8")
        except UnicodeEncodeError as error:
            raise ValueError("display_name must contain valid Unicode scalar values.") from error
        if not self.display_name.strip() or len(self.display_name) > _MAX_DISPLAY_NAME_LENGTH:
            raise ValueError("display_name must contain 1-512 usable characters.")
        if any(ord(character) < 0x20 for character in self.display_name):
            raise ValueError("display_name must not contain control characters.")
        validate_idempotency_key(self.idempotency_key)
        if (
            type(self.employment_status_code) is not str
            or _STATUS_CODE_PATTERN.fullmatch(self.employment_status_code) is None
        ):
            raise ValueError("employment_status_code must be a lower snake_case code.")


@dataclass(frozen=True, slots=True)
class HireAcceptanceResult:
    """Opaque authoritative identities returned after one committed hire mutation."""

    person_record_id: UUID
    employment_record_id: UUID
    candidate_worker_conversion_record_id: UUID

    def __post_init__(self) -> None:
        """Prevent malformed persistence results from crossing the service boundary."""
        for field_name in (
            "person_record_id",
            "employment_record_id",
            "candidate_worker_conversion_record_id",
        ):
            _validate_operational_uuid(field_name, getattr(self, field_name))


@runtime_checkable
class HireAcceptancePort(Protocol):
    """Persist one authorized hire atomically inside an Orgmetra-owned boundary."""

    def accept_hire(
        self,
        *,
        command: HireAcceptanceCommand,
        authorization: AuthorizationDecision,
    ) -> HireAcceptanceResult:
        """Materialize authoritative hire facts or raise without partial persistence."""


def accept_confirmed_hire(
    *,
    principal: AuthenticatedPrincipal,
    command: HireAcceptanceCommand,
    purpose_code: str,
    policy: PurposeBoundAccessPolicy,
    mutation_port: HireAcceptancePort,
) -> HireAcceptanceResult:
    """Authorize an exact confirmed decision before materializing worker truth.

    The authorization target is the immutable selection decision rather than a
    not-yet-created Person record. The policy must explicitly allow the
    ``materialize_worker`` operation and ``candidate_worker_conversion`` field;
    possession of an identity token or purpose string alone is insufficient.
    """
    if type(command) is not HireAcceptanceCommand:
        raise TypeError("command must be a HireAcceptanceCommand")
    command = replace(command)
    expected_person_record_id = UUID(int=command.person_record_id.int)
    expected_employment_record_id = UUID(int=command.employment_record_id.int)
    expected_conversion_record_id = UUID(
        int=command.candidate_worker_conversion_record_id.int
    )
    if not isinstance(mutation_port, HireAcceptancePort):
        raise TypeError("mutation_port must implement HireAcceptancePort")

    authorization = authorize_resource_fields(
        principal=principal,
        tenant_record_id=command.tenant_record_id,
        resource_tenant_record_id=command.tenant_record_id,
        resource_reference=f"selection_decision:{command.selection_decision_id.hex}",
        purpose_code=purpose_code,
        operation_code="materialize_worker",
        resource_kind="selection_decision",
        requested_fields=_HIRE_MUTATION_FIELDS,
        policy=policy,
    )
    result = mutation_port.accept_hire(command=command, authorization=authorization)
    if type(result) is not HireAcceptanceResult:
        raise TypeError("mutation_port must return HireAcceptanceResult")
    HireAcceptanceResult.__post_init__(result)
    if (
        result.person_record_id != expected_person_record_id
        or result.employment_record_id != expected_employment_record_id
        or result.candidate_worker_conversion_record_id != expected_conversion_record_id
    ):
        raise HireDecisionIntegrityError("hire result identity does not match command")
    return result
