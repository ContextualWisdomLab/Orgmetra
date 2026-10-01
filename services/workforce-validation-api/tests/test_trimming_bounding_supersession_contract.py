"""Regression contract for append-only trimming/bounding corrections."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from inspect import signature
from uuid import uuid4

import pytest

from orgmetra_workforce_validation_api.trimming_bounding_authority import (
    TrimmingBoundingAuthorityReadPort,
    TrimmingBoundingAuthorityRecord,
)
from orgmetra_workforce_validation_api.trimming_bounding_supersession_authority import (
    TrimmingBoundingSupersessionAuthorityRecord,
)


def _released_at() -> datetime:
    """Return a stable aware instant for correction chronology."""
    return datetime(2026, 9, 18, 1, 30, tzinfo=timezone.utc)


def _record(**overrides: object) -> TrimmingBoundingSupersessionAuthorityRecord:
    """Build one predecessor/successor edge with an atomic cutover."""
    released_at = _released_at()
    values: dict[str, object] = {
        "tenant_record_id": uuid4(),
        "validity_study_id": uuid4(),
        "adjustment_receipt_reference": "trimming_bounding_adjustment_receipt:old",
        "adjustment_receipt_digest": "a" * 64,
        "evidence_version": 1,
        "owner_contract_reference": "released_owner_contract:weighting-v1",
        "owner_contract_version": 1,
        "owner_contract_digest": "b" * 64,
        "owner_contract_released_at": released_at - timedelta(minutes=5),
        "released_at": released_at,
        "superseded_at": released_at + timedelta(minutes=10),
        "successor_adjustment_receipt_reference": "trimming_bounding_adjustment_receipt:new",
        "successor_adjustment_receipt_digest": "c" * 64,
        "successor_evidence_version": 1,
        "successor_released_at": released_at + timedelta(minutes=10),
    }
    values.update(overrides)
    return TrimmingBoundingSupersessionAuthorityRecord(**values)


def test_ordinary_trimming_authority_keeps_cutover_owner_resolved() -> None:
    """Currentness has a cutover without turning chronology into lookup identity."""
    assert "superseded_at" in signature(TrimmingBoundingAuthorityRecord).parameters
    read_parameters = signature(
        TrimmingBoundingAuthorityReadPort.read_trimming_bounding_authority
    ).parameters
    assert "superseded_at" not in read_parameters
    assert "owner_contract_released_at" not in read_parameters
    assert "released_at" not in read_parameters


def test_trimming_supersession_requires_atomic_successor_release() -> None:
    """A correction edge cannot create an overlap or gap around cutover."""
    _record()
    with pytest.raises(ValueError, match="exactly at supersession"):
        _record(successor_released_at=_released_at() + timedelta(minutes=11))


def test_trimming_supersession_requires_complete_new_successor() -> None:
    """A cutover must identify one complete new immutable successor receipt."""
    with pytest.raises(ValueError, match="complete released successor"):
        _record(successor_released_at=None)
    with pytest.raises(ValueError, match="new reference"):
        _record(
            successor_adjustment_receipt_reference="trimming_bounding_adjustment_receipt:old"
        )
    with pytest.raises(ValueError, match="new evidence"):
        _record(successor_adjustment_receipt_digest="a" * 64)
