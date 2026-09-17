"""Corroborate released calibration benchmark authority through its owner port.

This application boundary verifies the immutable benchmark coordinates carried by
scientific weighting evidence without copying benchmark values or reading another
bounded context's tables. Durable PostgreSQL/release resolution remains a child
persistence responsibility after this owner service integrates.
"""

from __future__ import annotations

from datetime import datetime
from inspect import getattr_static
import re
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

_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_REFERENCE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$")
_RESOURCE_KIND = "calibration_benchmark_authority"
_OPERATION = "read"
_READ_FIELDS = frozenset(
    {
        "benchmark_receipt_reference",
        "benchmark_receipt_version",
        "benchmark_receipt_digest",
        "benchmark_owner_contract_reference",
        "benchmark_owner_contract_version",
        "benchmark_owner_contract_digest",
        "benchmark_reference_at",
        "benchmark_receipt_released_at",
        "owner_contract_released_at",
    }
)


class CalibrationBenchmarkAuthorityNotFound(LookupError):
    """Indicate that no released owner evidence corroborates the benchmark tuple."""


class CalibrationBenchmarkAuthorityIntegrityError(RuntimeError):
    """Indicate that owner evidence cannot corroborate the requested benchmark tuple."""


def _require_reference(field_name: str, value: object, namespace: str) -> str:
    """Require one exact opaque namespaced reference without benchmark values."""
    if (
        type(value) is not str
        or _REFERENCE_PATTERN.fullmatch(value) is None
        or value.partition(":")[0] != namespace
    ):
        raise ValueError(f"{field_name} must be an exact {namespace}: opaque reference.")
    return value


def _require_digest(field_name: str, value: object) -> str:
    """Require lowercase SHA-256 evidence rather than caller-readable benchmark data."""
    if type(value) is not str or _DIGEST_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be lowercase SHA-256 hex.")
    return value


def _require_positive_integer(field_name: str, value: object) -> int:
    """Require a strict positive version without accepting booleans."""
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")
    return value


class CalibrationBenchmarkAuthorityRecord(tuple):
    """Immutable owner projection for one released calibration benchmark.

    The record contains only opaque references, versions, digests, and temporal
    release/correction evidence. Benchmark totals and protected source attributes
    never cross this application boundary.
    """

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        benchmark_receipt_reference: str,
        benchmark_receipt_version: int,
        benchmark_receipt_digest: str,
        benchmark_owner_contract_reference: str,
        benchmark_owner_contract_version: int,
        benchmark_owner_contract_digest: str,
        benchmark_reference_at: datetime,
        benchmark_receipt_released_at: datetime,
        owner_contract_released_at: datetime,
        benchmark_receipt_superseded_at: datetime | None = None,
        successor_benchmark_receipt_reference: str | None = None,
        successor_benchmark_receipt_version: int | None = None,
        successor_benchmark_receipt_digest: str | None = None,
        successor_benchmark_receipt_released_at: datetime | None = None,
    ) -> CalibrationBenchmarkAuthorityRecord:
        """Validate and detach all authority-bearing benchmark evidence."""
        tenant_identity = _store_operational_uuid("tenant_record_id", tenant_record_id)
        study_identity = _store_operational_uuid("validity_study_id", validity_study_id)
        benchmark_ref = _require_reference(
            "benchmark_receipt_reference",
            benchmark_receipt_reference,
            "calibration_benchmark_receipt",
        )
        benchmark_version = _require_positive_integer(
            "benchmark_receipt_version", benchmark_receipt_version
        )
        benchmark_digest = _require_digest(
            "benchmark_receipt_digest", benchmark_receipt_digest
        )
        owner_ref = _require_reference(
            "benchmark_owner_contract_reference",
            benchmark_owner_contract_reference,
            "released_owner_contract",
        )
        owner_version = _require_positive_integer(
            "benchmark_owner_contract_version", benchmark_owner_contract_version
        )
        owner_digest = _require_digest(
            "benchmark_owner_contract_digest", benchmark_owner_contract_digest
        )
        reference_at = _require_aware_datetime(
            "benchmark_reference_at", benchmark_reference_at
        )
        benchmark_released_at = _require_aware_datetime(
            "benchmark_receipt_released_at", benchmark_receipt_released_at
        )
        contract_released_at = _require_aware_datetime(
            "owner_contract_released_at", owner_contract_released_at
        )
        if contract_released_at > benchmark_released_at:
            raise ValueError(
                "owner contract must be released no later than benchmark receipt."
            )

        supersession_values = (
            benchmark_receipt_superseded_at,
            successor_benchmark_receipt_reference,
            successor_benchmark_receipt_version,
            successor_benchmark_receipt_digest,
            successor_benchmark_receipt_released_at,
        )
        if all(value is None for value in supersession_values):
            superseded_at = None
            successor_ref = None
            successor_version = None
            successor_digest = None
            successor_released_at = None
        elif any(value is None for value in supersession_values):
            raise ValueError(
                "benchmark supersession requires time and complete released successor coordinates."
            )
        else:
            superseded_at = _require_aware_datetime(
                "benchmark_receipt_superseded_at", benchmark_receipt_superseded_at
            )
            successor_ref = _require_reference(
                "successor_benchmark_receipt_reference",
                successor_benchmark_receipt_reference,
                "calibration_benchmark_receipt",
            )
            successor_version = _require_positive_integer(
                "successor_benchmark_receipt_version",
                successor_benchmark_receipt_version,
            )
            successor_digest = _require_digest(
                "successor_benchmark_receipt_digest",
                successor_benchmark_receipt_digest,
            )
            successor_released_at = _require_aware_datetime(
                "successor_benchmark_receipt_released_at",
                successor_benchmark_receipt_released_at,
            )
            if superseded_at < benchmark_released_at:
                raise ValueError(
                    "benchmark_receipt_superseded_at cannot precede release."
                )
            if successor_version <= benchmark_version:
                raise ValueError(
                    "successor benchmark receipt version must advance monotonically."
                )
            if successor_digest == benchmark_digest:
                raise ValueError(
                    "successor benchmark receipt digest must identify new evidence."
                )
            if successor_released_at <= benchmark_released_at:
                raise ValueError(
                    "successor benchmark receipt must be released after its predecessor."
                )
            if successor_released_at > superseded_at:
                raise ValueError(
                    "successor benchmark receipt must be released no later than supersession."
                )

        return tuple.__new__(
            cls,
            (
                tenant_identity,
                study_identity,
                benchmark_ref,
                benchmark_version,
                benchmark_digest,
                owner_ref,
                owner_version,
                owner_digest,
                reference_at,
                benchmark_released_at,
                contract_released_at,
                superseded_at,
                successor_ref,
                successor_version,
                successor_digest,
                successor_released_at,
            ),
        )

    @property
    def tenant_record_id(self) -> UUID:
        """Return a fresh tenant identity for this owner evidence."""
        return _restore_operational_uuid("tenant_record_id", self[0])

    @property
    def validity_study_id(self) -> UUID:
        """Return a fresh validity-study identity bound to this benchmark use."""
        return _restore_operational_uuid("validity_study_id", self[1])

    @property
    def benchmark_receipt_reference(self) -> str:
        """Return the immutable calibration-benchmark receipt reference."""
        return self[2]

    @property
    def benchmark_receipt_version(self) -> int:
        """Return the positive benchmark receipt version."""
        return self[3]

    @property
    def benchmark_receipt_digest(self) -> str:
        """Return the digest of the exact benchmark receipt bytes."""
        return self[4]

    @property
    def benchmark_owner_contract_reference(self) -> str:
        """Return the released benchmark-owner contract reference."""
        return self[5]

    @property
    def benchmark_owner_contract_version(self) -> int:
        """Return the released benchmark-owner contract version."""
        return self[6]

    @property
    def benchmark_owner_contract_digest(self) -> str:
        """Return the digest of the released benchmark-owner contract."""
        return self[7]

    @property
    def benchmark_reference_at(self) -> datetime:
        """Return the benchmark's authoritative reference instant."""
        return self[8]

    @property
    def benchmark_receipt_released_at(self) -> datetime:
        """Return when the benchmark receipt became released evidence."""
        return self[9]

    @property
    def owner_contract_released_at(self) -> datetime:
        """Return when the benchmark-owner contract became released evidence."""
        return self[10]

    @property
    def benchmark_receipt_superseded_at(self) -> datetime | None:
        """Return when this receipt stopped authorizing new scientific use."""
        return self[11]

    @property
    def successor_benchmark_receipt_reference(self) -> str | None:
        """Return the append-only successor receipt reference when corrected."""
        return self[12]

    @property
    def successor_benchmark_receipt_version(self) -> int | None:
        """Return the monotonically advanced successor receipt version."""
        return self[13]

    @property
    def successor_benchmark_receipt_digest(self) -> str | None:
        """Return the immutable successor evidence digest when corrected."""
        return self[14]

    @property
    def successor_benchmark_receipt_released_at(self) -> datetime | None:
        """Return when the owner released the append-only successor evidence."""
        return self[15]


class CalibrationBenchmarkAuthorityView(tuple):
    """Field-minimized benchmark evidence issued only after authorization."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        fields: tuple[tuple[str, object], ...],
    ) -> CalibrationBenchmarkAuthorityView:
        """Reject direct construction; only the resolver may issue this view."""
        raise TypeError(
            "CalibrationBenchmarkAuthorityView is issued only by "
            "resolve_calibration_benchmark_authority."
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
        """Return immutable released benchmark evidence without benchmark values."""
        return self[2]


@runtime_checkable
class CalibrationBenchmarkAuthorityReadPort(Protocol):
    """Owner read contract for released/versioned calibration benchmark evidence."""

    def read_calibration_benchmark_authority(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        benchmark_receipt_reference: str,
        benchmark_receipt_version: int,
        benchmark_receipt_digest: str,
        benchmark_owner_contract_reference: str,
        benchmark_owner_contract_version: int,
        benchmark_owner_contract_digest: str,
        benchmark_reference_at: datetime,
    ) -> CalibrationBenchmarkAuthorityRecord | None:
        """Return matching released evidence or ``None`` through an owner ACL."""
        ...


_PROTOCOL_READ_CAPABILITY = getattr_static(
    CalibrationBenchmarkAuthorityReadPort, "read_calibration_benchmark_authority"
)


def resolve_calibration_benchmark_authority(
    *,
    principal: ValidationPrincipal,
    tenant_record_id: UUID,
    validity_study_id: UUID,
    benchmark_receipt_reference: str,
    benchmark_receipt_version: int,
    benchmark_receipt_digest: str,
    benchmark_owner_contract_reference: str,
    benchmark_owner_contract_version: int,
    benchmark_owner_contract_digest: str,
    benchmark_reference_at: datetime,
    used_at: datetime,
    purpose_code: str,
    policy: PurposeBoundAccessPolicy,
    read_port: CalibrationBenchmarkAuthorityReadPort,
) -> CalibrationBenchmarkAuthorityView:
    """Authorize then corroborate the exact released benchmark tuple.

    The owner must independently resolve immutable release coordinates, release
    instants, and append-only correction lineage. ``used_at`` is the scientific
    receipt's use instant; it cannot precede release/reference authority or fall
    on/after the receipt's owner-resolved supersession instant. No benchmark totals
    or successor coordinates are returned to the caller.
    """
    if type(principal) is not ValidationPrincipal:
        raise TypeError("principal must be an exact ValidationPrincipal.")
    if type(policy) is not PurposeBoundAccessPolicy:
        raise TypeError("policy must be an exact PurposeBoundAccessPolicy.")
    read_capability = getattr_static(
        type(read_port), "read_calibration_benchmark_authority", None
    )
    if (
        type(read_capability) is not FunctionType
        or read_capability is _PROTOCOL_READ_CAPABILITY
    ):
        raise TypeError(
            "read_port must expose a statically callable "
            "read_calibration_benchmark_authority."
        )

    detached_principal = ValidationPrincipal(
        tenant_record_id=principal.tenant_record_id,
        actor_reference=principal.actor_reference,
        granted_scope_codes=principal.granted_scope_codes,
    )
    tenant_identity = _store_operational_uuid("tenant_record_id", tenant_record_id)
    study_identity = _store_operational_uuid("validity_study_id", validity_study_id)
    tenant_id = _restore_operational_uuid("tenant_record_id", tenant_identity)
    study_id = _restore_operational_uuid("validity_study_id", study_identity)
    benchmark_ref = _require_reference(
        "benchmark_receipt_reference",
        benchmark_receipt_reference,
        "calibration_benchmark_receipt",
    )
    benchmark_version = _require_positive_integer(
        "benchmark_receipt_version", benchmark_receipt_version
    )
    benchmark_digest = _require_digest(
        "benchmark_receipt_digest", benchmark_receipt_digest
    )
    owner_ref = _require_reference(
        "benchmark_owner_contract_reference",
        benchmark_owner_contract_reference,
        "released_owner_contract",
    )
    owner_version = _require_positive_integer(
        "benchmark_owner_contract_version", benchmark_owner_contract_version
    )
    owner_digest = _require_digest(
        "benchmark_owner_contract_digest", benchmark_owner_contract_digest
    )
    reference_at = _require_aware_datetime(
        "benchmark_reference_at", benchmark_reference_at
    )
    use_instant = _require_aware_datetime("used_at", used_at)
    purpose = _require_code("purpose_code", purpose_code)
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
        tenant_record_id=_restore_operational_uuid("tenant_record_id", tenant_identity),
        validity_study_id=_restore_operational_uuid("validity_study_id", study_identity),
        benchmark_receipt_reference=benchmark_ref,
        benchmark_receipt_version=benchmark_version,
        benchmark_receipt_digest=benchmark_digest,
        benchmark_owner_contract_reference=owner_ref,
        benchmark_owner_contract_version=owner_version,
        benchmark_owner_contract_digest=owner_digest,
        benchmark_reference_at=reference_at,
    )
    if persisted is None:
        raise CalibrationBenchmarkAuthorityNotFound(str(study_id))
    if type(persisted) is not CalibrationBenchmarkAuthorityRecord:
        raise CalibrationBenchmarkAuthorityIntegrityError(
            "owner port returned non-canonical calibration benchmark evidence"
        )

    record = CalibrationBenchmarkAuthorityRecord(
        tenant_record_id=persisted.tenant_record_id,
        validity_study_id=persisted.validity_study_id,
        benchmark_receipt_reference=persisted.benchmark_receipt_reference,
        benchmark_receipt_version=persisted.benchmark_receipt_version,
        benchmark_receipt_digest=persisted.benchmark_receipt_digest,
        benchmark_owner_contract_reference=persisted.benchmark_owner_contract_reference,
        benchmark_owner_contract_version=persisted.benchmark_owner_contract_version,
        benchmark_owner_contract_digest=persisted.benchmark_owner_contract_digest,
        benchmark_reference_at=persisted.benchmark_reference_at,
        benchmark_receipt_released_at=persisted.benchmark_receipt_released_at,
        owner_contract_released_at=persisted.owner_contract_released_at,
        benchmark_receipt_superseded_at=persisted.benchmark_receipt_superseded_at,
        successor_benchmark_receipt_reference=(
            persisted.successor_benchmark_receipt_reference
        ),
        successor_benchmark_receipt_version=(
            persisted.successor_benchmark_receipt_version
        ),
        successor_benchmark_receipt_digest=persisted.successor_benchmark_receipt_digest,
        successor_benchmark_receipt_released_at=(
            persisted.successor_benchmark_receipt_released_at
        ),
    )
    expected = (
        tenant_id,
        study_id,
        benchmark_ref,
        benchmark_version,
        benchmark_digest,
        owner_ref,
        owner_version,
        owner_digest,
        reference_at,
    )
    observed = (
        record.tenant_record_id,
        record.validity_study_id,
        record.benchmark_receipt_reference,
        record.benchmark_receipt_version,
        record.benchmark_receipt_digest,
        record.benchmark_owner_contract_reference,
        record.benchmark_owner_contract_version,
        record.benchmark_owner_contract_digest,
        record.benchmark_reference_at,
    )
    if observed != expected:
        raise CalibrationBenchmarkAuthorityIntegrityError(
            "released benchmark authority does not match the requested scientific coordinates"
        )
    if (
        record.benchmark_reference_at > use_instant
        or record.benchmark_receipt_released_at > use_instant
        or record.owner_contract_released_at > use_instant
    ):
        raise CalibrationBenchmarkAuthorityIntegrityError(
            "benchmark and owner evidence must exist no later than the scientific use instant"
        )
    if (
        record.benchmark_receipt_superseded_at is not None
        and record.benchmark_receipt_superseded_at <= use_instant
    ):
        raise CalibrationBenchmarkAuthorityIntegrityError(
            "superseded benchmark evidence cannot authorize scientific use at or after correction"
        )

    fields: tuple[tuple[str, object], ...] = (
        ("benchmark_owner_contract_digest", record.benchmark_owner_contract_digest),
        ("benchmark_owner_contract_reference", record.benchmark_owner_contract_reference),
        ("benchmark_owner_contract_version", record.benchmark_owner_contract_version),
        ("benchmark_receipt_digest", record.benchmark_receipt_digest),
        ("benchmark_receipt_reference", record.benchmark_receipt_reference),
        ("benchmark_receipt_released_at", record.benchmark_receipt_released_at),
        ("benchmark_receipt_version", record.benchmark_receipt_version),
        ("benchmark_reference_at", record.benchmark_reference_at),
        ("owner_contract_released_at", record.owner_contract_released_at),
    )
    return tuple.__new__(
        CalibrationBenchmarkAuthorityView,
        (
            _store_operational_uuid("tenant_record_id", tenant_id),
            _store_operational_uuid("validity_study_id", study_id),
            fields,
        ),
    )
