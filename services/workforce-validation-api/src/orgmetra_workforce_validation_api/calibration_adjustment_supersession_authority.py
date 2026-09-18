"""Corroborate append-only typed calibration-adjustment correction authority.

The ordinary calibration projection proves which released calibration receipt
produced a point-weight artifact. This boundary proves the half-open authority
interval for that immutable receipt and, when corrected, the exact released
successor that ends the interval. Successor chronology is owner-resolved and is
never accepted as a caller-selected lookup coordinate.
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

_RESOURCE_KIND = "calibration_adjustment_supersession_authority"
_OPERATION = "read"
_READ_FIELDS = frozenset(
    {
        "calibration_receipt_reference",
        "calibration_receipt_digest",
        "evidence_version",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "released_at",
        "superseded_at",
        "successor_calibration_receipt_reference",
        "successor_calibration_receipt_digest",
        "successor_evidence_version",
        "successor_released_at",
    }
)


class CalibrationAdjustmentSupersessionAuthorityNotFound(LookupError):
    """Indicate that no released owner evidence corroborates the calibration receipt."""


class CalibrationAdjustmentSupersessionAuthorityIntegrityError(RuntimeError):
    """Indicate that released calibration correction evidence cannot authorize use."""


class CalibrationAdjustmentSupersessionAuthorityRecord(tuple):
    """Immutable owner projection for one calibration receipt authority interval."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        calibration_receipt_reference: str,
        calibration_receipt_digest: str,
        evidence_version: int,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
        owner_contract_released_at: datetime,
        released_at: datetime,
        superseded_at: datetime | None = None,
        successor_calibration_receipt_reference: str | None = None,
        successor_calibration_receipt_digest: str | None = None,
        successor_evidence_version: int | None = None,
        successor_released_at: datetime | None = None,
    ) -> CalibrationAdjustmentSupersessionAuthorityRecord:
        """Validate one released predecessor and its optional atomic successor edge."""
        tenant_identity = _store_operational_uuid("tenant_record_id", tenant_record_id)
        study_identity = _store_operational_uuid("validity_study_id", validity_study_id)
        receipt_ref = _require_reference(
            "calibration_receipt_reference",
            calibration_receipt_reference,
            "calibration_adjustment_receipt",
        )
        receipt_digest = _require_digest(
            "calibration_receipt_digest", calibration_receipt_digest
        )
        version = _require_positive_integer("evidence_version", evidence_version)
        if version != 1:
            raise ValueError("evidence_version must remain 1.")
        owner_ref = _require_reference(
            "owner_contract_reference", owner_contract_reference, "released_owner_contract"
        )
        owner_version = _require_positive_integer(
            "owner_contract_version", owner_contract_version
        )
        owner_digest = _require_digest("owner_contract_digest", owner_contract_digest)
        owner_release = _require_aware_datetime(
            "owner_contract_released_at", owner_contract_released_at
        )
        release_instant = _require_aware_datetime("released_at", released_at)
        if owner_release > release_instant:
            raise ValueError(
                "owner contract must be released no later than calibration receipt."
            )

        successor_values = (
            superseded_at,
            successor_calibration_receipt_reference,
            successor_calibration_receipt_digest,
            successor_evidence_version,
            successor_released_at,
        )
        if all(value is None for value in successor_values):
            cutover = None
            successor_ref = None
            successor_digest = None
            successor_version = None
            successor_release = None
        elif any(value is None for value in successor_values):
            raise ValueError(
                "calibration supersession requires cutover and complete released successor coordinates."
            )
        else:
            cutover = _require_aware_datetime("superseded_at", superseded_at)
            successor_ref = _require_reference(
                "successor_calibration_receipt_reference",
                successor_calibration_receipt_reference,
                "calibration_adjustment_receipt",
            )
            successor_digest = _require_digest(
                "successor_calibration_receipt_digest",
                successor_calibration_receipt_digest,
            )
            successor_version = _require_positive_integer(
                "successor_evidence_version", successor_evidence_version
            )
            successor_release = _require_aware_datetime(
                "successor_released_at", successor_released_at
            )
            if cutover <= release_instant:
                raise ValueError("superseded_at must be later than calibration receipt release.")
            if successor_ref == receipt_ref:
                raise ValueError("successor calibration receipt must have a new reference.")
            if successor_digest == receipt_digest:
                raise ValueError("successor calibration receipt must identify new evidence.")
            if successor_version != 1:
                raise ValueError("successor_evidence_version must remain 1.")
            if successor_release <= release_instant:
                raise ValueError(
                    "successor calibration receipt must be released after its predecessor."
                )
            if successor_release != cutover:
                raise ValueError(
                    "successor calibration receipt must be released exactly at supersession."
                )

        current_fields: tuple[tuple[str, object], ...] = (
            ("calibration_receipt_digest", receipt_digest),
            ("calibration_receipt_reference", receipt_ref),
            ("evidence_version", version),
            ("owner_contract_digest", owner_digest),
            ("owner_contract_reference", owner_ref),
            ("owner_contract_released_at", owner_release),
            ("owner_contract_version", owner_version),
        )
        successor_fields: tuple[tuple[str, object], ...] | None
        if cutover is None:
            successor_fields = None
        else:
            successor_fields = (
                ("successor_calibration_receipt_digest", successor_digest),
                ("successor_calibration_receipt_reference", successor_ref),
                ("successor_evidence_version", successor_version),
                ("successor_released_at", successor_release),
            )
        return tuple.__new__(
            cls,
            (
                tenant_identity,
                study_identity,
                current_fields,
                release_instant,
                cutover,
                successor_fields,
            ),
        )

    @property
    def tenant_record_id(self) -> UUID:
        """Return a fresh tenant identity."""
        return _restore_operational_uuid("tenant_record_id", self[0])

    @property
    def validity_study_id(self) -> UUID:
        """Return a fresh validity-study identity."""
        return _restore_operational_uuid("validity_study_id", self[1])

    @property
    def fields(self) -> tuple[tuple[str, object], ...]:
        """Return immutable current-receipt authority coordinates."""
        return self[2]

    @property
    def released_at(self) -> datetime:
        """Return when this calibration receipt became released authority."""
        return self[3]

    @property
    def superseded_at(self) -> datetime | None:
        """Return the exclusive end of this receipt's authority interval."""
        return self[4]

    @property
    def successor_fields(self) -> tuple[tuple[str, object], ...] | None:
        """Return internal released successor coordinates, if any."""
        return self[5]


class CalibrationAdjustmentSupersessionAuthorityView(tuple):
    """Minimized current-receipt authority issued only after authorization."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        fields: tuple[tuple[str, object], ...],
    ) -> CalibrationAdjustmentSupersessionAuthorityView:
        """Reject public construction; only the resolver may issue this view."""
        raise TypeError(
            "CalibrationAdjustmentSupersessionAuthorityView is issued only by "
            "resolve_calibration_adjustment_supersession_authority."
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
        """Return current receipt authority without successor disclosure."""
        return self[2]


@runtime_checkable
class CalibrationAdjustmentSupersessionAuthorityReadPort(Protocol):
    """Owner read contract for one released calibration correction state."""

    def read_calibration_adjustment_supersession_authority(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        calibration_receipt_reference: str,
        calibration_receipt_digest: str,
        evidence_version: int,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
    ) -> CalibrationAdjustmentSupersessionAuthorityRecord | None:
        """Return matching released calibration supersession evidence or ``None``."""
        ...


_PROTOCOL_READ_CAPABILITY = getattr_static(
    CalibrationAdjustmentSupersessionAuthorityReadPort,
    "read_calibration_adjustment_supersession_authority",
)


def resolve_calibration_adjustment_supersession_authority(
    *,
    principal: ValidationPrincipal,
    tenant_record_id: UUID,
    validity_study_id: UUID,
    calibration_receipt_reference: str,
    calibration_receipt_digest: str,
    evidence_version: int,
    owner_contract_reference: str,
    owner_contract_version: int,
    owner_contract_digest: str,
    used_at: datetime,
    purpose_code: str,
    policy: PurposeBoundAccessPolicy,
    read_port: CalibrationAdjustmentSupersessionAuthorityReadPort,
) -> CalibrationAdjustmentSupersessionAuthorityView:
    """Authorize then resolve the receipt's half-open append-only authority interval."""
    if type(principal) is not ValidationPrincipal:
        raise TypeError("principal must be an exact ValidationPrincipal.")
    if type(policy) is not PurposeBoundAccessPolicy:
        raise TypeError("policy must be an exact PurposeBoundAccessPolicy.")
    read_capability = getattr_static(
        type(read_port), "read_calibration_adjustment_supersession_authority", None
    )
    if (
        type(read_capability) is not FunctionType
        or read_capability is _PROTOCOL_READ_CAPABILITY
    ):
        raise TypeError(
            "read_port must expose a statically callable "
            "read_calibration_adjustment_supersession_authority."
        )

    tenant_id = _restore_operational_uuid(
        "tenant_record_id", _store_operational_uuid("tenant_record_id", tenant_record_id)
    )
    study_id = _restore_operational_uuid(
        "validity_study_id", _store_operational_uuid("validity_study_id", validity_study_id)
    )
    receipt_ref = _require_reference(
        "calibration_receipt_reference",
        calibration_receipt_reference,
        "calibration_adjustment_receipt",
    )
    receipt_digest = _require_digest(
        "calibration_receipt_digest", calibration_receipt_digest
    )
    version = _require_positive_integer("evidence_version", evidence_version)
    if version != 1:
        raise ValueError("evidence_version must remain 1.")
    owner_ref = _require_reference(
        "owner_contract_reference", owner_contract_reference, "released_owner_contract"
    )
    owner_version = _require_positive_integer("owner_contract_version", owner_contract_version)
    owner_digest = _require_digest("owner_contract_digest", owner_contract_digest)
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
        tenant_record_id=tenant_id,
        validity_study_id=study_id,
        calibration_receipt_reference=receipt_ref,
        calibration_receipt_digest=receipt_digest,
        evidence_version=version,
        owner_contract_reference=owner_ref,
        owner_contract_version=owner_version,
        owner_contract_digest=owner_digest,
    )
    if persisted is None:
        raise CalibrationAdjustmentSupersessionAuthorityNotFound(str(study_id))
    if type(persisted) is not CalibrationAdjustmentSupersessionAuthorityRecord:
        raise CalibrationAdjustmentSupersessionAuthorityIntegrityError(
            "owner port returned non-canonical calibration supersession evidence"
        )

    try:
        persisted_fields = dict(persisted.fields)
        persisted_successor = (
            None if persisted.successor_fields is None else dict(persisted.successor_fields)
        )
        record = CalibrationAdjustmentSupersessionAuthorityRecord(
            tenant_record_id=persisted.tenant_record_id,
            validity_study_id=persisted.validity_study_id,
            calibration_receipt_reference=persisted_fields[
                "calibration_receipt_reference"
            ],
            calibration_receipt_digest=persisted_fields[
                "calibration_receipt_digest"
            ],
            evidence_version=persisted_fields["evidence_version"],
            owner_contract_reference=persisted_fields["owner_contract_reference"],
            owner_contract_version=persisted_fields["owner_contract_version"],
            owner_contract_digest=persisted_fields["owner_contract_digest"],
            owner_contract_released_at=persisted_fields["owner_contract_released_at"],
            released_at=persisted.released_at,
            superseded_at=persisted.superseded_at,
            successor_calibration_receipt_reference=(
                None
                if persisted_successor is None
                else persisted_successor["successor_calibration_receipt_reference"]
            ),
            successor_calibration_receipt_digest=(
                None
                if persisted_successor is None
                else persisted_successor["successor_calibration_receipt_digest"]
            ),
            successor_evidence_version=(
                None
                if persisted_successor is None
                else persisted_successor["successor_evidence_version"]
            ),
            successor_released_at=(
                None
                if persisted_successor is None
                else persisted_successor["successor_released_at"]
            ),
        )
    except (IndexError, KeyError, TypeError, ValueError) as exc:
        raise CalibrationAdjustmentSupersessionAuthorityIntegrityError(
            "owner port returned malformed calibration supersession evidence"
        ) from exc
    if record != persisted:
        raise CalibrationAdjustmentSupersessionAuthorityIntegrityError(
            "owner port returned non-canonical calibration supersession structure"
        )

    record_values = dict(record.fields)
    if (
        _store_operational_uuid("record tenant_record_id", record.tenant_record_id)
        != _store_operational_uuid("requested tenant_record_id", tenant_id)
        or _store_operational_uuid("record validity_study_id", record.validity_study_id)
        != _store_operational_uuid("requested validity_study_id", study_id)
        or record_values["calibration_receipt_reference"] != receipt_ref
        or record_values["calibration_receipt_digest"] != receipt_digest
        or record_values["evidence_version"] != version
        or record_values["owner_contract_reference"] != owner_ref
        or record_values["owner_contract_version"] != owner_version
        or record_values["owner_contract_digest"] != owner_digest
    ):
        raise CalibrationAdjustmentSupersessionAuthorityIntegrityError(
            "released calibration supersession authority does not match requested coordinates"
        )
    if use_instant < record.released_at:
        raise CalibrationAdjustmentSupersessionAuthorityIntegrityError(
            "calibration receipt must be released before scientific use"
        )
    if record.superseded_at is not None and use_instant >= record.superseded_at:
        raise CalibrationAdjustmentSupersessionAuthorityIntegrityError(
            "calibration receipt is superseded for this scientific-use instant"
        )

    fields = record.fields + (
        ("released_at", record.released_at),
        ("superseded_at", record.superseded_at),
    )
    return tuple.__new__(
        CalibrationAdjustmentSupersessionAuthorityView,
        (
            _store_operational_uuid("tenant_record_id", tenant_id),
            _store_operational_uuid("validity_study_id", study_id),
            fields,
        ),
    )
