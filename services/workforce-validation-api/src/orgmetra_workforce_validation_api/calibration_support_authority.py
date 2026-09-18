"""Corroborate released auxiliary/benchmark chronology for one calibration receipt.

The typed calibration receipt carries the identities of the auxiliary and benchmark
inputs used to construct weights. This boundary separately proves that those exact
supporting authorities were released and current when the calibration was
constructed. Owner-resolved release, effective-interval, and cutover instants are
evidence rather than caller lookup coordinates.
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

_RESOURCE_KIND = "calibration_support_authority"
_OPERATION = "read"
_READ_FIELDS = frozenset(
    {
        "support_authority_reference",
        "support_authority_digest",
        "evidence_version",
        "calibration_receipt_reference",
        "calibration_receipt_digest",
        "auxiliary_authority_reference",
        "auxiliary_projection_reference",
        "auxiliary_projection_version",
        "auxiliary_projection_digest",
        "auxiliary_purpose_reference",
        "auxiliary_purpose_digest",
        "auxiliary_owner_contract_reference",
        "auxiliary_owner_contract_version",
        "auxiliary_owner_contract_digest",
        "auxiliary_owner_contract_released_at",
        "auxiliary_authorization_receipt_reference",
        "auxiliary_authorization_receipt_digest",
        "auxiliary_authorization_receipt_released_at",
        "auxiliary_scientific_use_receipt_reference",
        "auxiliary_scientific_use_receipt_digest",
        "auxiliary_scientific_use_at",
        "auxiliary_authorized_from",
        "auxiliary_authorized_to",
        "benchmark_receipt_reference",
        "benchmark_receipt_version",
        "benchmark_receipt_digest",
        "benchmark_owner_contract_reference",
        "benchmark_owner_contract_version",
        "benchmark_owner_contract_digest",
        "benchmark_owner_contract_released_at",
        "benchmark_reference_at",
        "benchmark_receipt_released_at",
        "benchmark_receipt_superseded_at",
        "constructed_at",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "released_at",
    }
)


class CalibrationSupportAuthorityNotFound(LookupError):
    """Indicate that no released support binding matches the requested calibration."""


class CalibrationSupportAuthorityIntegrityError(RuntimeError):
    """Indicate that returned support evidence does not match the requested binding."""


def _tuple_property(index: int, doc: str) -> property:
    """Create a documented immutable tuple projection for one public evidence field."""

    def getter(record: tuple[object, ...]) -> object:
        """Return one already-validated immutable evidence coordinate."""
        return record[index]

    return property(getter, doc=doc)


class CalibrationSupportAuthorityRecord(tuple):
    """Immutable released proof that calibration support was valid at construction."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        support_authority_reference: str,
        support_authority_digest: str,
        evidence_version: int,
        calibration_receipt_reference: str,
        calibration_receipt_digest: str,
        auxiliary_authority_reference: str,
        auxiliary_projection_reference: str,
        auxiliary_projection_version: int,
        auxiliary_projection_digest: str,
        auxiliary_purpose_reference: str,
        auxiliary_purpose_digest: str,
        auxiliary_owner_contract_reference: str,
        auxiliary_owner_contract_version: int,
        auxiliary_owner_contract_digest: str,
        auxiliary_owner_contract_released_at: datetime,
        auxiliary_authorization_receipt_reference: str,
        auxiliary_authorization_receipt_digest: str,
        auxiliary_authorization_receipt_released_at: datetime,
        auxiliary_scientific_use_receipt_reference: str,
        auxiliary_scientific_use_receipt_digest: str,
        auxiliary_scientific_use_at: datetime,
        auxiliary_authorized_from: datetime,
        auxiliary_authorized_to: datetime | None,
        benchmark_receipt_reference: str,
        benchmark_receipt_version: int,
        benchmark_receipt_digest: str,
        benchmark_owner_contract_reference: str,
        benchmark_owner_contract_version: int,
        benchmark_owner_contract_digest: str,
        benchmark_owner_contract_released_at: datetime,
        benchmark_reference_at: datetime,
        benchmark_receipt_released_at: datetime,
        benchmark_receipt_superseded_at: datetime | None,
        constructed_at: datetime,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
        owner_contract_released_at: datetime,
        released_at: datetime,
    ) -> CalibrationSupportAuthorityRecord:
        """Validate identities and chronology before storing detached owner evidence."""
        tenant_identity = _store_operational_uuid("tenant_record_id", tenant_record_id)
        study_identity = _store_operational_uuid("validity_study_id", validity_study_id)
        support_ref = _require_reference(
            "support_authority_reference",
            support_authority_reference,
            "calibration_support_authority",
        )
        support_digest = _require_digest("support_authority_digest", support_authority_digest)
        version = _require_positive_integer("evidence_version", evidence_version)
        if version != 1:
            raise ValueError("evidence_version must remain 1.")
        calibration_ref = _require_reference(
            "calibration_receipt_reference",
            calibration_receipt_reference,
            "calibration_adjustment_receipt",
        )
        calibration_digest = _require_digest(
            "calibration_receipt_digest", calibration_receipt_digest
        )
        auxiliary_authority_ref = _require_reference(
            "auxiliary_authority_reference",
            auxiliary_authority_reference,
            "scientific_auxiliary_authority",
        )
        projection_ref = _require_reference(
            "auxiliary_projection_reference",
            auxiliary_projection_reference,
            "calibration_auxiliary_projection",
        )
        projection_version = _require_positive_integer(
            "auxiliary_projection_version", auxiliary_projection_version
        )
        projection_digest = _require_digest(
            "auxiliary_projection_digest", auxiliary_projection_digest
        )
        purpose_ref = _require_reference(
            "auxiliary_purpose_reference",
            auxiliary_purpose_reference,
            "scientific_data_use_purpose",
        )
        purpose_digest = _require_digest("auxiliary_purpose_digest", auxiliary_purpose_digest)
        auxiliary_owner_ref = _require_reference(
            "auxiliary_owner_contract_reference",
            auxiliary_owner_contract_reference,
            "released_owner_contract",
        )
        auxiliary_owner_version = _require_positive_integer(
            "auxiliary_owner_contract_version", auxiliary_owner_contract_version
        )
        auxiliary_owner_digest = _require_digest(
            "auxiliary_owner_contract_digest", auxiliary_owner_contract_digest
        )
        auxiliary_owner_released = _require_aware_datetime(
            "auxiliary_owner_contract_released_at", auxiliary_owner_contract_released_at
        )
        authorization_ref = _require_reference(
            "auxiliary_authorization_receipt_reference",
            auxiliary_authorization_receipt_reference,
            "scientific_data_authorization",
        )
        authorization_digest = _require_digest(
            "auxiliary_authorization_receipt_digest", auxiliary_authorization_receipt_digest
        )
        authorization_released = _require_aware_datetime(
            "auxiliary_authorization_receipt_released_at",
            auxiliary_authorization_receipt_released_at,
        )
        use_ref = _require_reference(
            "auxiliary_scientific_use_receipt_reference",
            auxiliary_scientific_use_receipt_reference,
            "scientific_use_receipt",
        )
        use_digest = _require_digest(
            "auxiliary_scientific_use_receipt_digest", auxiliary_scientific_use_receipt_digest
        )
        use_at = _require_aware_datetime(
            "auxiliary_scientific_use_at", auxiliary_scientific_use_at
        )
        authorized_from = _require_aware_datetime(
            "auxiliary_authorized_from", auxiliary_authorized_from
        )
        authorized_to = (
            None
            if auxiliary_authorized_to is None
            else _require_aware_datetime("auxiliary_authorized_to", auxiliary_authorized_to)
        )
        if auxiliary_owner_released > authorization_released:
            raise ValueError("auxiliary owner contract cannot postdate authorization receipt.")
        if authorization_released > use_at:
            raise ValueError(
                "authorization receipt must be released no later than auxiliary scientific use."
            )
        if authorization_released > authorized_from:
            raise ValueError(
                "authorization receipt must exist before authorization begins."
            )
        if authorized_to is not None and authorized_to <= authorized_from:
            raise ValueError("auxiliary_authorized_to must be later than auxiliary_authorized_from.")
        if use_at < authorized_from or (authorized_to is not None and use_at >= authorized_to):
            raise ValueError(
                "auxiliary scientific use must fall inside owner-resolved authorization interval."
            )

        benchmark_ref = _require_reference(
            "benchmark_receipt_reference",
            benchmark_receipt_reference,
            "calibration_benchmark_receipt",
        )
        benchmark_version = _require_positive_integer(
            "benchmark_receipt_version", benchmark_receipt_version
        )
        benchmark_digest = _require_digest("benchmark_receipt_digest", benchmark_receipt_digest)
        benchmark_owner_ref = _require_reference(
            "benchmark_owner_contract_reference",
            benchmark_owner_contract_reference,
            "released_owner_contract",
        )
        benchmark_owner_version = _require_positive_integer(
            "benchmark_owner_contract_version", benchmark_owner_contract_version
        )
        benchmark_owner_digest = _require_digest(
            "benchmark_owner_contract_digest", benchmark_owner_contract_digest
        )
        benchmark_owner_released = _require_aware_datetime(
            "benchmark_owner_contract_released_at", benchmark_owner_contract_released_at
        )
        benchmark_reference = _require_aware_datetime(
            "benchmark_reference_at", benchmark_reference_at
        )
        benchmark_released = _require_aware_datetime(
            "benchmark_receipt_released_at", benchmark_receipt_released_at
        )
        benchmark_superseded = (
            None
            if benchmark_receipt_superseded_at is None
            else _require_aware_datetime(
                "benchmark_receipt_superseded_at", benchmark_receipt_superseded_at
            )
        )
        if benchmark_owner_released > benchmark_released:
            raise ValueError("benchmark owner contract cannot postdate benchmark receipt release.")
        if benchmark_superseded is not None and benchmark_superseded <= benchmark_released:
            raise ValueError("benchmark supersession must be later than benchmark receipt release.")

        constructed = _require_aware_datetime("constructed_at", constructed_at)
        if use_at > constructed:
            raise ValueError("auxiliary scientific use cannot be later than calibration construction.")
        if benchmark_reference > constructed:
            raise ValueError("benchmark reference cannot be later than calibration construction.")
        if benchmark_released > constructed:
            raise ValueError("benchmark receipt must be released no later than calibration construction.")
        if benchmark_superseded is not None and constructed >= benchmark_superseded:
            raise ValueError(
                "superseded benchmark cannot support calibration construction at or after cutover."
            )

        owner_ref = _require_reference(
            "owner_contract_reference", owner_contract_reference, "released_owner_contract"
        )
        owner_version = _require_positive_integer("owner_contract_version", owner_contract_version)
        owner_digest = _require_digest("owner_contract_digest", owner_contract_digest)
        owner_released = _require_aware_datetime(
            "owner_contract_released_at", owner_contract_released_at
        )
        released = _require_aware_datetime("released_at", released_at)
        if owner_released > released:
            raise ValueError("owner contract cannot be released after support evidence.")
        if released < constructed:
            raise ValueError("support evidence cannot be released before calibration construction.")

        return tuple.__new__(
            cls,
            (
                tenant_identity,
                study_identity,
                support_ref,
                support_digest,
                version,
                calibration_ref,
                calibration_digest,
                auxiliary_authority_ref,
                projection_ref,
                projection_version,
                projection_digest,
                purpose_ref,
                purpose_digest,
                auxiliary_owner_ref,
                auxiliary_owner_version,
                auxiliary_owner_digest,
                auxiliary_owner_released,
                authorization_ref,
                authorization_digest,
                authorization_released,
                use_ref,
                use_digest,
                use_at,
                authorized_from,
                authorized_to,
                benchmark_ref,
                benchmark_version,
                benchmark_digest,
                benchmark_owner_ref,
                benchmark_owner_version,
                benchmark_owner_digest,
                benchmark_owner_released,
                benchmark_reference,
                benchmark_released,
                benchmark_superseded,
                constructed,
                owner_ref,
                owner_version,
                owner_digest,
                owner_released,
                released,
            ),
        )

    @property
    def tenant_record_id(self) -> UUID:
        """Return a fresh tenant identity for this support authority."""
        return _restore_operational_uuid("tenant_record_id", self[0])

    @property
    def validity_study_id(self) -> UUID:
        """Return a fresh validity-study identity for this support authority."""
        return _restore_operational_uuid("validity_study_id", self[1])

    support_authority_reference = _tuple_property(2, "Return the immutable support-authority reference.")
    support_authority_digest = _tuple_property(3, "Return the digest of the exact support-authority evidence.")
    evidence_version = _tuple_property(4, "Return the governed support-authority evidence version.")
    calibration_receipt_reference = _tuple_property(5, "Return the typed calibration receipt this support proof corroborates.")
    calibration_receipt_digest = _tuple_property(6, "Return the digest of the typed calibration receipt.")
    auxiliary_authority_reference = _tuple_property(7, "Return the scientific auxiliary-authority identity used by calibration.")
    auxiliary_projection_reference = _tuple_property(8, "Return the purpose-limited auxiliary projection reference.")
    auxiliary_projection_version = _tuple_property(9, "Return the exact auxiliary projection version.")
    auxiliary_projection_digest = _tuple_property(10, "Return the digest of the auxiliary projection used by calibration.")
    auxiliary_purpose_reference = _tuple_property(11, "Return the governed scientific-use purpose reference.")
    auxiliary_purpose_digest = _tuple_property(12, "Return the digest of the governed scientific-use purpose.")
    auxiliary_owner_contract_reference = _tuple_property(13, "Return the released auxiliary-owner contract reference.")
    auxiliary_owner_contract_version = _tuple_property(14, "Return the released auxiliary-owner contract version.")
    auxiliary_owner_contract_digest = _tuple_property(15, "Return the released auxiliary-owner contract digest.")
    auxiliary_owner_contract_released_at = _tuple_property(16, "Return when the auxiliary-owner contract became released evidence.")
    auxiliary_authorization_receipt_reference = _tuple_property(17, "Return the purpose-bound authorization receipt reference.")
    auxiliary_authorization_receipt_digest = _tuple_property(18, "Return the digest of the purpose-bound authorization receipt.")
    auxiliary_authorization_receipt_released_at = _tuple_property(19, "Return when the authorization receipt became released evidence.")
    auxiliary_scientific_use_receipt_reference = _tuple_property(20, "Return the immutable scientific-use receipt reference.")
    auxiliary_scientific_use_receipt_digest = _tuple_property(21, "Return the digest of the scientific-use receipt.")
    auxiliary_scientific_use_at = _tuple_property(22, "Return the scientific-use instant committed by the calibration lineage.")
    auxiliary_authorized_from = _tuple_property(23, "Return the inclusive start of the owner-resolved authorization interval.")
    auxiliary_authorized_to = _tuple_property(24, "Return the optional exclusive end of the owner-resolved authorization interval.")
    benchmark_receipt_reference = _tuple_property(25, "Return the calibration benchmark receipt reference.")
    benchmark_receipt_version = _tuple_property(26, "Return the exact calibration benchmark receipt version.")
    benchmark_receipt_digest = _tuple_property(27, "Return the digest of the exact calibration benchmark receipt.")
    benchmark_owner_contract_reference = _tuple_property(28, "Return the released benchmark-owner contract reference.")
    benchmark_owner_contract_version = _tuple_property(29, "Return the released benchmark-owner contract version.")
    benchmark_owner_contract_digest = _tuple_property(30, "Return the released benchmark-owner contract digest.")
    benchmark_owner_contract_released_at = _tuple_property(31, "Return when the benchmark-owner contract became released evidence.")
    benchmark_reference_at = _tuple_property(32, "Return the benchmark reference instant committed by calibration.")
    benchmark_receipt_released_at = _tuple_property(33, "Return when the benchmark receipt became released evidence.")
    benchmark_receipt_superseded_at = _tuple_property(34, "Return the optional exclusive cutover that ended benchmark authority.")
    constructed_at = _tuple_property(35, "Return when the typed calibration receipt was constructed.")
    owner_contract_reference = _tuple_property(36, "Return the released application owner-contract reference.")
    owner_contract_version = _tuple_property(37, "Return the released application owner-contract version.")
    owner_contract_digest = _tuple_property(38, "Return the digest of the released application owner contract.")
    owner_contract_released_at = _tuple_property(39, "Return when the application owner contract became released evidence.")
    released_at = _tuple_property(40, "Return when this support proof became released application evidence.")


class CalibrationSupportAuthorityView(tuple):
    """Field-minimized support evidence issued only after purpose-bound authorization."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        fields: tuple[tuple[str, object], ...],
    ) -> CalibrationSupportAuthorityView:
        """Reject direct construction so callers cannot mint reusable authority views."""
        raise TypeError(
            "CalibrationSupportAuthorityView is issued only by resolve_calibration_support_authority."
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
        """Return immutable corroborating support evidence without source values."""
        return self[2]


@runtime_checkable
class CalibrationSupportAuthorityReadPort(Protocol):
    """Owner read contract keyed only by caller-known immutable coordinates."""

    def read_calibration_support_authority(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        calibration_receipt_reference: str,
        calibration_receipt_digest: str,
        auxiliary_authority_reference: str,
        auxiliary_projection_reference: str,
        auxiliary_projection_version: int,
        auxiliary_projection_digest: str,
        auxiliary_purpose_reference: str,
        auxiliary_purpose_digest: str,
        auxiliary_owner_contract_reference: str,
        auxiliary_owner_contract_version: int,
        auxiliary_owner_contract_digest: str,
        auxiliary_authorization_receipt_reference: str,
        auxiliary_authorization_receipt_digest: str,
        auxiliary_scientific_use_receipt_reference: str,
        auxiliary_scientific_use_receipt_digest: str,
        auxiliary_scientific_use_at: datetime,
        benchmark_receipt_reference: str,
        benchmark_receipt_version: int,
        benchmark_receipt_digest: str,
        benchmark_owner_contract_reference: str,
        benchmark_owner_contract_version: int,
        benchmark_owner_contract_digest: str,
        benchmark_reference_at: datetime,
        constructed_at: datetime,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
    ) -> CalibrationSupportAuthorityRecord | None:
        """Return matching released support evidence or ``None`` through an owner ACL."""
        ...


_PROTOCOL_READ_CAPABILITY = getattr_static(
    CalibrationSupportAuthorityReadPort, "read_calibration_support_authority"
)


def _caller_coordinates(record: CalibrationSupportAuthorityRecord) -> tuple[object, ...]:
    """Return immutable caller-known coordinates while excluding owner chronology."""
    return (
        record.tenant_record_id,
        record.validity_study_id,
        record.calibration_receipt_reference,
        record.calibration_receipt_digest,
        record.auxiliary_authority_reference,
        record.auxiliary_projection_reference,
        record.auxiliary_projection_version,
        record.auxiliary_projection_digest,
        record.auxiliary_purpose_reference,
        record.auxiliary_purpose_digest,
        record.auxiliary_owner_contract_reference,
        record.auxiliary_owner_contract_version,
        record.auxiliary_owner_contract_digest,
        record.auxiliary_authorization_receipt_reference,
        record.auxiliary_authorization_receipt_digest,
        record.auxiliary_scientific_use_receipt_reference,
        record.auxiliary_scientific_use_receipt_digest,
        record.auxiliary_scientific_use_at,
        record.benchmark_receipt_reference,
        record.benchmark_receipt_version,
        record.benchmark_receipt_digest,
        record.benchmark_owner_contract_reference,
        record.benchmark_owner_contract_version,
        record.benchmark_owner_contract_digest,
        record.benchmark_reference_at,
        record.constructed_at,
        record.owner_contract_reference,
        record.owner_contract_version,
        record.owner_contract_digest,
    )


def resolve_calibration_support_authority(
    *,
    principal: ValidationPrincipal,
    tenant_record_id: UUID,
    validity_study_id: UUID,
    calibration_receipt_reference: str,
    calibration_receipt_digest: str,
    auxiliary_authority_reference: str,
    auxiliary_projection_reference: str,
    auxiliary_projection_version: int,
    auxiliary_projection_digest: str,
    auxiliary_purpose_reference: str,
    auxiliary_purpose_digest: str,
    auxiliary_owner_contract_reference: str,
    auxiliary_owner_contract_version: int,
    auxiliary_owner_contract_digest: str,
    auxiliary_authorization_receipt_reference: str,
    auxiliary_authorization_receipt_digest: str,
    auxiliary_scientific_use_receipt_reference: str,
    auxiliary_scientific_use_receipt_digest: str,
    auxiliary_scientific_use_at: datetime,
    benchmark_receipt_reference: str,
    benchmark_receipt_version: int,
    benchmark_receipt_digest: str,
    benchmark_owner_contract_reference: str,
    benchmark_owner_contract_version: int,
    benchmark_owner_contract_digest: str,
    benchmark_reference_at: datetime,
    constructed_at: datetime,
    owner_contract_reference: str,
    owner_contract_version: int,
    owner_contract_digest: str,
    used_at: datetime,
    purpose_code: str,
    policy: PurposeBoundAccessPolicy,
    read_port: CalibrationSupportAuthorityReadPort,
) -> CalibrationSupportAuthorityView:
    """Authorize and resolve released support chronology for one calibration receipt."""
    if type(principal) is not ValidationPrincipal:
        raise TypeError("principal must be an exact ValidationPrincipal.")
    if type(policy) is not PurposeBoundAccessPolicy:
        raise TypeError("policy must be an exact PurposeBoundAccessPolicy.")
    read_capability = getattr_static(type(read_port), "read_calibration_support_authority", None)
    if type(read_capability) is not FunctionType or read_capability is _PROTOCOL_READ_CAPABILITY:
        raise TypeError(
            "read_port must expose a statically callable read_calibration_support_authority."
        )

    tenant_identity = _store_operational_uuid("tenant_record_id", tenant_record_id)
    study_identity = _store_operational_uuid("validity_study_id", validity_study_id)
    tenant_id = _restore_operational_uuid("tenant_record_id", tenant_identity)
    study_id = _restore_operational_uuid("validity_study_id", study_identity)
    use_instant = _require_aware_datetime("used_at", used_at)
    purpose = _require_code("purpose_code", purpose_code)
    detached_principal = ValidationPrincipal(
        tenant_record_id=principal.tenant_record_id,
        actor_reference=principal.actor_reference,
        granted_scope_codes=principal.granted_scope_codes,
    )
    detached_policy = _detach_policy(policy)

    calibration_ref = _require_reference(
        "calibration_receipt_reference", calibration_receipt_reference, "calibration_adjustment_receipt"
    )
    calibration_digest = _require_digest("calibration_receipt_digest", calibration_receipt_digest)
    auxiliary_authority_ref = _require_reference(
        "auxiliary_authority_reference", auxiliary_authority_reference, "scientific_auxiliary_authority"
    )
    projection_ref = _require_reference(
        "auxiliary_projection_reference", auxiliary_projection_reference, "calibration_auxiliary_projection"
    )
    projection_version = _require_positive_integer(
        "auxiliary_projection_version", auxiliary_projection_version
    )
    projection_digest = _require_digest("auxiliary_projection_digest", auxiliary_projection_digest)
    purpose_ref = _require_reference(
        "auxiliary_purpose_reference", auxiliary_purpose_reference, "scientific_data_use_purpose"
    )
    purpose_digest = _require_digest("auxiliary_purpose_digest", auxiliary_purpose_digest)
    auxiliary_owner_ref = _require_reference(
        "auxiliary_owner_contract_reference", auxiliary_owner_contract_reference, "released_owner_contract"
    )
    auxiliary_owner_version = _require_positive_integer(
        "auxiliary_owner_contract_version", auxiliary_owner_contract_version
    )
    auxiliary_owner_digest = _require_digest(
        "auxiliary_owner_contract_digest", auxiliary_owner_contract_digest
    )
    authorization_ref = _require_reference(
        "auxiliary_authorization_receipt_reference",
        auxiliary_authorization_receipt_reference,
        "scientific_data_authorization",
    )
    authorization_digest = _require_digest(
        "auxiliary_authorization_receipt_digest", auxiliary_authorization_receipt_digest
    )
    scientific_use_ref = _require_reference(
        "auxiliary_scientific_use_receipt_reference",
        auxiliary_scientific_use_receipt_reference,
        "scientific_use_receipt",
    )
    scientific_use_digest = _require_digest(
        "auxiliary_scientific_use_receipt_digest", auxiliary_scientific_use_receipt_digest
    )
    scientific_use_at = _require_aware_datetime(
        "auxiliary_scientific_use_at", auxiliary_scientific_use_at
    )
    benchmark_ref = _require_reference(
        "benchmark_receipt_reference", benchmark_receipt_reference, "calibration_benchmark_receipt"
    )
    benchmark_version = _require_positive_integer("benchmark_receipt_version", benchmark_receipt_version)
    benchmark_digest = _require_digest("benchmark_receipt_digest", benchmark_receipt_digest)
    benchmark_owner_ref = _require_reference(
        "benchmark_owner_contract_reference", benchmark_owner_contract_reference, "released_owner_contract"
    )
    benchmark_owner_version = _require_positive_integer(
        "benchmark_owner_contract_version", benchmark_owner_contract_version
    )
    benchmark_owner_digest = _require_digest(
        "benchmark_owner_contract_digest", benchmark_owner_contract_digest
    )
    benchmark_reference = _require_aware_datetime("benchmark_reference_at", benchmark_reference_at)
    constructed = _require_aware_datetime("constructed_at", constructed_at)
    owner_ref = _require_reference(
        "owner_contract_reference", owner_contract_reference, "released_owner_contract"
    )
    owner_version = _require_positive_integer("owner_contract_version", owner_contract_version)
    owner_digest = _require_digest("owner_contract_digest", owner_contract_digest)

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
        tenant_record_id=tenant_id,
        validity_study_id=study_id,
        calibration_receipt_reference=calibration_ref,
        calibration_receipt_digest=calibration_digest,
        auxiliary_authority_reference=auxiliary_authority_ref,
        auxiliary_projection_reference=projection_ref,
        auxiliary_projection_version=projection_version,
        auxiliary_projection_digest=projection_digest,
        auxiliary_purpose_reference=purpose_ref,
        auxiliary_purpose_digest=purpose_digest,
        auxiliary_owner_contract_reference=auxiliary_owner_ref,
        auxiliary_owner_contract_version=auxiliary_owner_version,
        auxiliary_owner_contract_digest=auxiliary_owner_digest,
        auxiliary_authorization_receipt_reference=authorization_ref,
        auxiliary_authorization_receipt_digest=authorization_digest,
        auxiliary_scientific_use_receipt_reference=scientific_use_ref,
        auxiliary_scientific_use_receipt_digest=scientific_use_digest,
        auxiliary_scientific_use_at=scientific_use_at,
        benchmark_receipt_reference=benchmark_ref,
        benchmark_receipt_version=benchmark_version,
        benchmark_receipt_digest=benchmark_digest,
        benchmark_owner_contract_reference=benchmark_owner_ref,
        benchmark_owner_contract_version=benchmark_owner_version,
        benchmark_owner_contract_digest=benchmark_owner_digest,
        benchmark_reference_at=benchmark_reference,
        constructed_at=constructed,
        owner_contract_reference=owner_ref,
        owner_contract_version=owner_version,
        owner_contract_digest=owner_digest,
    )
    if persisted is None:
        raise CalibrationSupportAuthorityNotFound(str(study_id))
    if type(persisted) is not CalibrationSupportAuthorityRecord:
        raise CalibrationSupportAuthorityIntegrityError(
            "owner port returned non-canonical calibration support authority evidence"
        )

    record = CalibrationSupportAuthorityRecord(
        tenant_record_id=persisted.tenant_record_id,
        validity_study_id=persisted.validity_study_id,
        support_authority_reference=persisted.support_authority_reference,
        support_authority_digest=persisted.support_authority_digest,
        evidence_version=persisted.evidence_version,
        calibration_receipt_reference=persisted.calibration_receipt_reference,
        calibration_receipt_digest=persisted.calibration_receipt_digest,
        auxiliary_authority_reference=persisted.auxiliary_authority_reference,
        auxiliary_projection_reference=persisted.auxiliary_projection_reference,
        auxiliary_projection_version=persisted.auxiliary_projection_version,
        auxiliary_projection_digest=persisted.auxiliary_projection_digest,
        auxiliary_purpose_reference=persisted.auxiliary_purpose_reference,
        auxiliary_purpose_digest=persisted.auxiliary_purpose_digest,
        auxiliary_owner_contract_reference=persisted.auxiliary_owner_contract_reference,
        auxiliary_owner_contract_version=persisted.auxiliary_owner_contract_version,
        auxiliary_owner_contract_digest=persisted.auxiliary_owner_contract_digest,
        auxiliary_owner_contract_released_at=persisted.auxiliary_owner_contract_released_at,
        auxiliary_authorization_receipt_reference=persisted.auxiliary_authorization_receipt_reference,
        auxiliary_authorization_receipt_digest=persisted.auxiliary_authorization_receipt_digest,
        auxiliary_authorization_receipt_released_at=persisted.auxiliary_authorization_receipt_released_at,
        auxiliary_scientific_use_receipt_reference=persisted.auxiliary_scientific_use_receipt_reference,
        auxiliary_scientific_use_receipt_digest=persisted.auxiliary_scientific_use_receipt_digest,
        auxiliary_scientific_use_at=persisted.auxiliary_scientific_use_at,
        auxiliary_authorized_from=persisted.auxiliary_authorized_from,
        auxiliary_authorized_to=persisted.auxiliary_authorized_to,
        benchmark_receipt_reference=persisted.benchmark_receipt_reference,
        benchmark_receipt_version=persisted.benchmark_receipt_version,
        benchmark_receipt_digest=persisted.benchmark_receipt_digest,
        benchmark_owner_contract_reference=persisted.benchmark_owner_contract_reference,
        benchmark_owner_contract_version=persisted.benchmark_owner_contract_version,
        benchmark_owner_contract_digest=persisted.benchmark_owner_contract_digest,
        benchmark_owner_contract_released_at=persisted.benchmark_owner_contract_released_at,
        benchmark_reference_at=persisted.benchmark_reference_at,
        benchmark_receipt_released_at=persisted.benchmark_receipt_released_at,
        benchmark_receipt_superseded_at=persisted.benchmark_receipt_superseded_at,
        constructed_at=persisted.constructed_at,
        owner_contract_reference=persisted.owner_contract_reference,
        owner_contract_version=persisted.owner_contract_version,
        owner_contract_digest=persisted.owner_contract_digest,
        owner_contract_released_at=persisted.owner_contract_released_at,
        released_at=persisted.released_at,
    )
    expected = (
        tenant_id,
        study_id,
        calibration_ref,
        calibration_digest,
        auxiliary_authority_ref,
        projection_ref,
        projection_version,
        projection_digest,
        purpose_ref,
        purpose_digest,
        auxiliary_owner_ref,
        auxiliary_owner_version,
        auxiliary_owner_digest,
        authorization_ref,
        authorization_digest,
        scientific_use_ref,
        scientific_use_digest,
        scientific_use_at,
        benchmark_ref,
        benchmark_version,
        benchmark_digest,
        benchmark_owner_ref,
        benchmark_owner_version,
        benchmark_owner_digest,
        benchmark_reference,
        constructed,
        owner_ref,
        owner_version,
        owner_digest,
    )
    if _caller_coordinates(record) != expected:
        raise CalibrationSupportAuthorityIntegrityError(
            "released calibration support authority does not match requested coordinates"
        )
    if record.released_at > use_instant:
        raise CalibrationSupportAuthorityIntegrityError(
            "calibration support evidence must be released before scientific use"
        )

    values = {field_name: getattr(record, field_name) for field_name in _READ_FIELDS}
    fields = tuple((field_name, values[field_name]) for field_name in sorted(_READ_FIELDS))
    return tuple.__new__(
        CalibrationSupportAuthorityView,
        (tenant_identity, study_identity, fields),
    )
