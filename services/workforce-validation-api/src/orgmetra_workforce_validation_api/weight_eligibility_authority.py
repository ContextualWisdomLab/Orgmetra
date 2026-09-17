"""Corroborate released cross-sectional/longitudinal weight eligibility.

The owner port binds one point-weight artifact to its governed population,
reference duration, eligible case set, and scope. It does not copy row-level
weights, person attributes, or foreign application data.
"""

from __future__ import annotations

from datetime import datetime
from inspect import getattr_static
from types import FunctionType
from typing import Protocol, runtime_checkable
from uuid import UUID

from orgmetra_keyverse_adapter import (
    PurposeBoundAccessPolicy,
    PurposeBoundAccessRequest,
    require_purpose_bound_access,
)

from .registry import (
    ValidationPrincipal,
    _detach_policy,
    _require_aware_datetime,
    _require_code,
    _restore_operational_uuid,
    _store_operational_uuid,
)
from .scientific_authority import (
    _require_digest,
    _require_positive_integer,
    _require_reference,
)

_RESOURCE_KIND = "weight_eligibility_authority"
_OPERATION = "read"
_WEIGHT_SCOPE_CODES = frozenset({"cross_sectional", "longitudinal"})
_READ_FIELDS = frozenset(
    {
        "eligibility_receipt_reference",
        "eligibility_receipt_digest",
        "evidence_version",
        "weight_scope_code",
        "target_population_reference",
        "target_population_digest",
        "reference_duration_reference",
        "reference_duration_digest",
        "eligible_case_set_digest",
        "weight_artifact_digest",
        "constructed_at",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "released_at",
    }
)


class WeightEligibilityAuthorityNotFound(LookupError):
    """Indicate that no released owner evidence corroborates the eligibility receipt."""


class WeightEligibilityAuthorityIntegrityError(RuntimeError):
    """Indicate that owner evidence cannot corroborate the requested eligibility tuple."""


def _require_weight_scope(value: object) -> str:
    """Require explicit cross-sectional or longitudinal eligibility semantics."""
    if type(value) is not str or value not in _WEIGHT_SCOPE_CODES:
        raise ValueError("weight_scope_code must be cross_sectional or longitudinal.")
    return value


class WeightEligibilityAuthorityRecord(tuple):
    """Immutable owner projection for one released weight-eligibility receipt."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        eligibility_receipt_reference: str,
        eligibility_receipt_digest: str,
        evidence_version: int,
        weight_scope_code: str,
        target_population_reference: str,
        target_population_digest: str,
        reference_duration_reference: str,
        reference_duration_digest: str,
        eligible_case_set_digest: str,
        weight_artifact_digest: str,
        constructed_at: datetime,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
        released_at: datetime,
    ) -> WeightEligibilityAuthorityRecord:
        """Validate and detach the minimum immutable eligibility authority."""
        tenant_identity = _store_operational_uuid("tenant_record_id", tenant_record_id)
        study_identity = _store_operational_uuid("validity_study_id", validity_study_id)
        receipt_ref = _require_reference(
            "eligibility_receipt_reference",
            eligibility_receipt_reference,
            "weight_eligibility_receipt",
        )
        receipt_digest = _require_digest(
            "eligibility_receipt_digest", eligibility_receipt_digest
        )
        version = _require_positive_integer("evidence_version", evidence_version)
        if version != 1:
            raise ValueError("evidence_version must remain 1.")
        scope = _require_weight_scope(weight_scope_code)
        target_ref = _require_reference(
            "target_population_reference",
            target_population_reference,
            "analysis_target_population",
        )
        target_digest = _require_digest(
            "target_population_digest", target_population_digest
        )
        duration_ref = _require_reference(
            "reference_duration_reference",
            reference_duration_reference,
            "analysis_reference_duration",
        )
        duration_digest = _require_digest(
            "reference_duration_digest", reference_duration_digest
        )
        case_digest = _require_digest(
            "eligible_case_set_digest", eligible_case_set_digest
        )
        artifact_digest = _require_digest(
            "weight_artifact_digest", weight_artifact_digest
        )
        constructed = _require_aware_datetime("constructed_at", constructed_at)
        owner_ref = _require_reference(
            "owner_contract_reference", owner_contract_reference, "released_owner_contract"
        )
        owner_version = _require_positive_integer(
            "owner_contract_version", owner_contract_version
        )
        owner_digest = _require_digest("owner_contract_digest", owner_contract_digest)
        release_instant = _require_aware_datetime("released_at", released_at)
        if release_instant < constructed:
            raise ValueError("released_at cannot precede constructed_at.")
        return tuple.__new__(
            cls,
            (
                tenant_identity,
                study_identity,
                receipt_ref,
                receipt_digest,
                version,
                scope,
                target_ref,
                target_digest,
                duration_ref,
                duration_digest,
                case_digest,
                artifact_digest,
                constructed,
                owner_ref,
                owner_version,
                owner_digest,
                release_instant,
            ),
        )

    @property
    def tenant_record_id(self) -> UUID:
        """Return a fresh tenant identity for this released evidence."""
        return _restore_operational_uuid("tenant_record_id", self[0])

    @property
    def validity_study_id(self) -> UUID:
        """Return a fresh validity-study identity for this released evidence."""
        return _restore_operational_uuid("validity_study_id", self[1])

    @property
    def eligibility_receipt_reference(self) -> str:
        """Return the typed weight-eligibility receipt reference."""
        return self[2]

    @property
    def eligibility_receipt_digest(self) -> str:
        """Return the exact eligibility receipt digest."""
        return self[3]

    @property
    def evidence_version(self) -> int:
        """Return the eligibility receipt evidence version."""
        return self[4]

    @property
    def weight_scope_code(self) -> str:
        """Return cross-sectional or longitudinal eligibility semantics."""
        return self[5]

    @property
    def target_population_reference(self) -> str:
        """Return the governed analysis target-population reference."""
        return self[6]

    @property
    def target_population_digest(self) -> str:
        """Return the target-population evidence digest."""
        return self[7]

    @property
    def reference_duration_reference(self) -> str:
        """Return the governed analysis reference-duration reference."""
        return self[8]

    @property
    def reference_duration_digest(self) -> str:
        """Return the reference-duration evidence digest."""
        return self[9]

    @property
    def eligible_case_set_digest(self) -> str:
        """Return the exact eligible-case set digest."""
        return self[10]

    @property
    def weight_artifact_digest(self) -> str:
        """Return the point-weight artifact governed by this eligibility receipt."""
        return self[11]

    @property
    def constructed_at(self) -> datetime:
        """Return when the typed eligibility receipt was constructed."""
        return self[12]

    @property
    def owner_contract_reference(self) -> str:
        """Return the released owner-contract reference."""
        return self[13]

    @property
    def owner_contract_version(self) -> int:
        """Return the released owner-contract version."""
        return self[14]

    @property
    def owner_contract_digest(self) -> str:
        """Return the released owner-contract digest."""
        return self[15]

    @property
    def released_at(self) -> datetime:
        """Return when this eligibility evidence became released authority."""
        return self[16]


class WeightEligibilityAuthorityView(tuple):
    """Field-minimized eligibility evidence issued only after authorization."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        fields: tuple[tuple[str, object], ...],
    ) -> WeightEligibilityAuthorityView:
        """Reject direct construction; only the resolver may issue this view."""
        raise TypeError(
            "WeightEligibilityAuthorityView is issued only by "
            "resolve_weight_eligibility_authority."
        )

    @property
    def tenant_record_id(self) -> UUID:
        """Return a fresh authorized tenant identity."""
        return _restore_operational_uuid("tenant_record_id", self[0])

    @property
    def validity_study_id(self) -> UUID:
        """Return a fresh authorized validity-study identity."""
        return _restore_operational_uuid("validity_study_id", self[1])

    @property
    def fields(self) -> tuple[tuple[str, object], ...]:
        """Return immutable eligibility provenance without row-level values."""
        return self[2]


@runtime_checkable
class WeightEligibilityAuthorityReadPort(Protocol):
    """Owner read contract for released typed weight-eligibility evidence."""

    def read_weight_eligibility_authority(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        eligibility_receipt_reference: str,
        eligibility_receipt_digest: str,
        evidence_version: int,
        weight_scope_code: str,
        target_population_reference: str,
        target_population_digest: str,
        reference_duration_reference: str,
        reference_duration_digest: str,
        eligible_case_set_digest: str,
        weight_artifact_digest: str,
        constructed_at: datetime,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
    ) -> WeightEligibilityAuthorityRecord | None:
        """Return matching released eligibility evidence or ``None``."""
        ...


_PROTOCOL_READ_CAPABILITY = getattr_static(
    WeightEligibilityAuthorityReadPort, "read_weight_eligibility_authority"
)


def resolve_weight_eligibility_authority(
    *,
    principal: ValidationPrincipal,
    tenant_record_id: UUID,
    validity_study_id: UUID,
    eligibility_receipt_reference: str,
    eligibility_receipt_digest: str,
    evidence_version: int,
    weight_scope_code: str,
    target_population_reference: str,
    target_population_digest: str,
    reference_duration_reference: str,
    reference_duration_digest: str,
    eligible_case_set_digest: str,
    weight_artifact_digest: str,
    constructed_at: datetime,
    owner_contract_reference: str,
    owner_contract_version: int,
    owner_contract_digest: str,
    used_at: datetime,
    purpose_code: str,
    policy: PurposeBoundAccessPolicy,
    read_port: WeightEligibilityAuthorityReadPort,
) -> WeightEligibilityAuthorityView:
    """Authorize then corroborate exact released weight-eligibility evidence."""
    if type(principal) is not ValidationPrincipal:
        raise TypeError("principal must be an exact ValidationPrincipal.")
    if type(policy) is not PurposeBoundAccessPolicy:
        raise TypeError("policy must be an exact PurposeBoundAccessPolicy.")
    read_capability = getattr_static(type(read_port), "read_weight_eligibility_authority", None)
    if (
        type(read_capability) is not FunctionType
        or read_capability is _PROTOCOL_READ_CAPABILITY
    ):
        raise TypeError(
            "read_port must expose a statically callable read_weight_eligibility_authority."
        )

    requested = WeightEligibilityAuthorityRecord(
        tenant_record_id=tenant_record_id,
        validity_study_id=validity_study_id,
        eligibility_receipt_reference=eligibility_receipt_reference,
        eligibility_receipt_digest=eligibility_receipt_digest,
        evidence_version=evidence_version,
        weight_scope_code=weight_scope_code,
        target_population_reference=target_population_reference,
        target_population_digest=target_population_digest,
        reference_duration_reference=reference_duration_reference,
        reference_duration_digest=reference_duration_digest,
        eligible_case_set_digest=eligible_case_set_digest,
        weight_artifact_digest=weight_artifact_digest,
        constructed_at=constructed_at,
        owner_contract_reference=owner_contract_reference,
        owner_contract_version=owner_contract_version,
        owner_contract_digest=owner_contract_digest,
        released_at=constructed_at,
    )
    tenant_id = requested.tenant_record_id
    study_id = requested.validity_study_id
    use_instant = _require_aware_datetime("used_at", used_at)
    purpose = _require_code("purpose_code", purpose_code)
    detached_principal = ValidationPrincipal(
        tenant_record_id=principal.tenant_record_id,
        actor_reference=principal.actor_reference,
        granted_scope_codes=principal.granted_scope_codes,
    )
    detached_policy = _detach_policy(policy)

    require_purpose_bound_access(
        request=PurposeBoundAccessRequest(
            tenant_record_id=tenant_id,
            actor_tenant_record_id=detached_principal.tenant_record_id,
            resource_tenant_record_id=tenant_id,
            actor_reference=detached_principal.actor_reference,
            resource_reference=f"{_RESOURCE_KIND}:{study_id}",
            purpose_code=purpose,
            operation_code=_OPERATION,
            resource_kind=_RESOURCE_KIND,
            requested_fields=_READ_FIELDS,
            granted_scope_codes=detached_principal.granted_scope_codes,
        ),
        policy=detached_policy,
    )

    persisted = read_capability(
        read_port,
        tenant_record_id=requested.tenant_record_id,
        validity_study_id=requested.validity_study_id,
        eligibility_receipt_reference=requested.eligibility_receipt_reference,
        eligibility_receipt_digest=requested.eligibility_receipt_digest,
        evidence_version=requested.evidence_version,
        weight_scope_code=requested.weight_scope_code,
        target_population_reference=requested.target_population_reference,
        target_population_digest=requested.target_population_digest,
        reference_duration_reference=requested.reference_duration_reference,
        reference_duration_digest=requested.reference_duration_digest,
        eligible_case_set_digest=requested.eligible_case_set_digest,
        weight_artifact_digest=requested.weight_artifact_digest,
        constructed_at=requested.constructed_at,
        owner_contract_reference=requested.owner_contract_reference,
        owner_contract_version=requested.owner_contract_version,
        owner_contract_digest=requested.owner_contract_digest,
    )
    if persisted is None:
        raise WeightEligibilityAuthorityNotFound(str(study_id))
    if type(persisted) is not WeightEligibilityAuthorityRecord:
        raise WeightEligibilityAuthorityIntegrityError(
            "owner port returned non-canonical weight-eligibility authority evidence"
        )

    record = WeightEligibilityAuthorityRecord(
        tenant_record_id=persisted.tenant_record_id,
        validity_study_id=persisted.validity_study_id,
        eligibility_receipt_reference=persisted.eligibility_receipt_reference,
        eligibility_receipt_digest=persisted.eligibility_receipt_digest,
        evidence_version=persisted.evidence_version,
        weight_scope_code=persisted.weight_scope_code,
        target_population_reference=persisted.target_population_reference,
        target_population_digest=persisted.target_population_digest,
        reference_duration_reference=persisted.reference_duration_reference,
        reference_duration_digest=persisted.reference_duration_digest,
        eligible_case_set_digest=persisted.eligible_case_set_digest,
        weight_artifact_digest=persisted.weight_artifact_digest,
        constructed_at=persisted.constructed_at,
        owner_contract_reference=persisted.owner_contract_reference,
        owner_contract_version=persisted.owner_contract_version,
        owner_contract_digest=persisted.owner_contract_digest,
        released_at=persisted.released_at,
    )
    if record[:-1] != requested[:-1]:
        raise WeightEligibilityAuthorityIntegrityError(
            "released weight-eligibility authority does not match requested coordinates"
        )
    if record.released_at > use_instant:
        raise WeightEligibilityAuthorityIntegrityError(
            "weight-eligibility evidence must be released before scientific use"
        )

    fields: tuple[tuple[str, object], ...] = (
        ("constructed_at", record.constructed_at),
        ("eligibility_receipt_digest", record.eligibility_receipt_digest),
        ("eligibility_receipt_reference", record.eligibility_receipt_reference),
        ("eligible_case_set_digest", record.eligible_case_set_digest),
        ("evidence_version", record.evidence_version),
        ("owner_contract_digest", record.owner_contract_digest),
        ("owner_contract_reference", record.owner_contract_reference),
        ("owner_contract_version", record.owner_contract_version),
        ("reference_duration_digest", record.reference_duration_digest),
        ("reference_duration_reference", record.reference_duration_reference),
        ("released_at", record.released_at),
        ("target_population_digest", record.target_population_digest),
        ("target_population_reference", record.target_population_reference),
        ("weight_artifact_digest", record.weight_artifact_digest),
        ("weight_scope_code", record.weight_scope_code),
    )
    return tuple.__new__(
        WeightEligibilityAuthorityView,
        (
            _store_operational_uuid("tenant_record_id", tenant_id),
            _store_operational_uuid("validity_study_id", study_id),
            fields,
        ),
    )
