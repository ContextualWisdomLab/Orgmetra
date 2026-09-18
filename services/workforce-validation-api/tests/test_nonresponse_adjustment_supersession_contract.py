"""Regression contract for append-only nonresponse-adjustment corrections."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from inspect import signature
from uuid import uuid4

import pytest

from orgmetra_workforce_validation_api.nonresponse_adjustment_authority import (
    NonresponseAdjustmentAuthorityRecord,
)
from orgmetra_workforce_validation_api.nonresponse_adjustment_supersession_authority import (
    NonresponseAdjustmentSupersessionAuthorityRecord,
)


def _released_at() -> datetime:
    """Return a stable aware instant for chronology assertions."""
    return datetime(2026, 9, 18, 1, 0, tzinfo=timezone.utc)


def _supersession_record(**overrides: object) -> NonresponseAdjustmentSupersessionAuthorityRecord:
    """Build one predecessor/successor edge with an atomic correction instant."""
    released_at = _released_at()
    values: dict[str, object] = {
        "tenant_record_id": uuid4(),
        "validity_study_id": uuid4(),
        "nonresponse_receipt_reference": "nonresponse_adjustment_receipt:old",
        "nonresponse_receipt_digest": "a" * 64,
        "evidence_version": 1,
        "owner_contract_reference": "released_owner_contract:weighting-v1",
        "owner_contract_version": 1,
        "owner_contract_digest": "b" * 64,
        "owner_contract_released_at": released_at - timedelta(minutes=5),
        "released_at": released_at,
        "superseded_at": released_at + timedelta(minutes=10),
        "successor_nonresponse_receipt_reference": "nonresponse_adjustment_receipt:new",
        "successor_nonresponse_receipt_digest": "c" * 64,
        "successor_evidence_version": 1,
        "successor_released_at": released_at + timedelta(minutes=10),
    }
    values.update(overrides)
    return NonresponseAdjustmentSupersessionAuthorityRecord(**values)


def test_ordinary_nonresponse_authority_keeps_cutover_owner_resolved() -> None:
    """Ordinary currentness accepts a cutover but never makes it a lookup coordinate."""
    record_parameters = signature(NonresponseAdjustmentAuthorityRecord).parameters
    assert "superseded_at" in record_parameters


def test_nonresponse_supersession_requires_atomic_successor_release() -> None:
    """A correction edge cannot leave an overlap or gap around the cutover."""
    _supersession_record()
    with pytest.raises(ValueError, match="exactly at supersession"):
        _supersession_record(
            successor_released_at=_released_at() + timedelta(minutes=11)
        )


def test_nonresponse_supersession_requires_new_immutable_evidence() -> None:
    """A predecessor cannot supersede itself or reuse its evidence digest."""
    with pytest.raises(ValueError, match="new reference"):
        _supersession_record(
            successor_nonresponse_receipt_reference="nonresponse_adjustment_receipt:old"
        )
    with pytest.raises(ValueError, match="new evidence"):
        _supersession_record(successor_nonresponse_receipt_digest="a" * 64)
