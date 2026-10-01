"""Governed-use currentness for exact final-weight component evidence."""

from __future__ import annotations

from datetime import timedelta

import pytest

from orgmetra_workforce_validation_api.final_weight_component_evidence_resolution import (
    FinalWeightComponentEvidenceIntegrityError,
)
from test_final_weight_component_evidence_resolution import (
    CONSTRUCTED_AT,
    _ReadPort,
    _adjustment_evidence,
    _base_evidence,
    _corroborate,
)


def test_base_component_superseded_after_construction_before_use_fails_closed() -> None:
    port = _ReadPort(
        base=_base_evidence(superseded_at=CONSTRUCTED_AT + timedelta(minutes=10))
    )
    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match="governed use"):
        _corroborate(read_port=port)


def test_adjustment_component_superseded_after_construction_before_use_fails_closed() -> None:
    port = _ReadPort(
        adjustment=_adjustment_evidence(
            superseded_at=CONSTRUCTED_AT + timedelta(minutes=10)
        )
    )
    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match="governed use"):
        _corroborate(read_port=port)
