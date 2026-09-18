"""Append-only correction contract for typed calibration-adjustment authority."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.calibration_adjustment_supersession_authority import (
    CalibrationAdjustmentSupersessionAuthorityIntegrityError,
    CalibrationAdjustmentSupersessionAuthorityReadPort,
    CalibrationAdjustmentSupersessionAuthorityRecord,
    resolve_calibration_adjustment_supersession_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
RECEIPT = "calibration_adjustment_receipt:11111111-1111-4111-8111-111111111111"
SUCCESSOR = "calibration_adjustment_receipt:22222222-2222-4222-8222-222222222222"
OWNER = "released_owner_contract:33333333-3333-4333-8333-333333333333"
DIGEST = "1" * 64
SUCCESSOR_DIGEST = "2" * 64
OWNER_DIGEST = "3" * 64
OWNER_RELEASED = datetime(2026, 9, 16, 12, 30, tzinfo=timezone.utc)
RELEASED = datetime(2026, 9, 16, 13, 0, tzinfo=timezone.utc)
CUTOVER = datetime(2026, 9, 17, 13, 0, tzinfo=timezone.utc)


class _ReadPort:
    def __init__(self, record: CalibrationAdjustmentSupersessionAuthorityRecord) -> None:
        self.record = record
        self.calls: list[dict[str, object]] = []

    def read_calibration_adjustment_supersession_authority(
        self, **coordinates: object
    ) -> CalibrationAdjustmentSupersessionAuthorityRecord:
        self.calls.append(dict(coordinates))
        return self.record


def _principal() -> ValidationPrincipal:
    return ValidationPrincipal(
        tenant_record_id=TENANT,
        actor_reference="person:validation-analyst-1",
        granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
    )


def _policy() -> PurposeBoundAccessPolicy:
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="calibration-adjustment-supersession-read-v1",
        resource_kind="calibration_adjustment_supersession_authority",
        purpose_code="selection_validity_analysis",
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=frozenset(
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
        ),
    )


def _record(**overrides: object) -> CalibrationAdjustmentSupersessionAuthorityRecord:
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "calibration_receipt_reference": RECEIPT,
        "calibration_receipt_digest": DIGEST,
        "evidence_version": 1,
        "owner_contract_reference": OWNER,
        "owner_contract_version": 1,
        "owner_contract_digest": OWNER_DIGEST,
        "owner_contract_released_at": OWNER_RELEASED,
        "released_at": RELEASED,
        "superseded_at": CUTOVER,
        "successor_calibration_receipt_reference": SUCCESSOR,
        "successor_calibration_receipt_digest": SUCCESSOR_DIGEST,
        "successor_evidence_version": 1,
        "successor_released_at": CUTOVER,
    }
    values.update(overrides)
    return CalibrationAdjustmentSupersessionAuthorityRecord(**values)


def _resolve(
    record: CalibrationAdjustmentSupersessionAuthorityRecord, *, used_at: datetime
):
    return resolve_calibration_adjustment_supersession_authority(
        principal=_principal(),
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        calibration_receipt_reference=RECEIPT,
        calibration_receipt_digest=DIGEST,
        evidence_version=1,
        owner_contract_reference=OWNER,
        owner_contract_version=1,
        owner_contract_digest=OWNER_DIGEST,
        used_at=used_at,
        purpose_code="selection_validity_analysis",
        policy=_policy(),
        read_port=_ReadPort(record),
    )


def test_successor_edge_requires_complete_atomic_released_coordinates() -> None:
    with pytest.raises(ValueError, match="complete released successor coordinates"):
        _record(successor_released_at=None)

    with pytest.raises(ValueError, match="exactly at supersession"):
        _record(successor_released_at=CUTOVER - timedelta(seconds=1))

    with pytest.raises(ValueError, match="exactly at supersession"):
        _record(successor_released_at=CUTOVER + timedelta(seconds=1))

    with pytest.raises(ValueError, match="new reference"):
        _record(successor_calibration_receipt_reference=RECEIPT)

    with pytest.raises(ValueError, match="new evidence"):
        _record(successor_calibration_receipt_digest=DIGEST)


def test_historical_use_is_allowed_but_cutover_use_fails_closed() -> None:
    record = _record()
    view = _resolve(record, used_at=CUTOVER - timedelta(microseconds=1))

    assert isinstance(_ReadPort(record), CalibrationAdjustmentSupersessionAuthorityReadPort)
    assert ("calibration_receipt_reference", RECEIPT) in view.fields
    assert all(not name.startswith("successor_") for name, _ in view.fields)

    with pytest.raises(
        CalibrationAdjustmentSupersessionAuthorityIntegrityError,
        match="superseded",
    ):
        _resolve(record, used_at=CUTOVER)


def test_open_interval_without_successor_remains_current() -> None:
    record = _record(
        superseded_at=None,
        successor_calibration_receipt_reference=None,
        successor_calibration_receipt_digest=None,
        successor_evidence_version=None,
        successor_released_at=None,
    )

    view = _resolve(record, used_at=CUTOVER + timedelta(days=30))
    assert ("released_at", RELEASED) in view.fields
    assert ("superseded_at", None) in view.fields
