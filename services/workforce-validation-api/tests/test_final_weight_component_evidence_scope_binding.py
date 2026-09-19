"""Tenant/study provenance for normalized final-weight component evidence."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from orgmetra_workforce_validation_api.final_weight_component_evidence_resolution import (
    AdjustmentComponentEvidence,
    BaseWeightComponentEvidence,
    FinalWeightComponentEvidenceIntegrityError,
    _canonical_adjustment_evidence,
    _canonical_base_evidence,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000f1")
RELEASED_AT = datetime(2026, 9, 19, 4, 0, tzinfo=timezone.utc)


def _base() -> BaseWeightComponentEvidence:
    return BaseWeightComponentEvidence(
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        receipt_reference="base_weight_evidence_receipt:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        receipt_digest="2" * 64,
        evidence_version=1,
        method_code="inverse_probability",
        method_version=1,
        output_weight_artifact_digest="3" * 64,
        released_at=RELEASED_AT,
    )


def _adjustment() -> AdjustmentComponentEvidence:
    return AdjustmentComponentEvidence(
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        evidence_kind="nonresponse_adjustment_receipt",
        receipt_reference="nonresponse_adjustment_receipt:cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        receipt_digest="4" * 64,
        evidence_version=1,
        method_reference="weight_method:dddddddd-dddd-4ddd-8ddd-dddddddddddd",
        method_version=1,
        input_weight_artifact_digest="3" * 64,
        output_weight_artifact_digest="5" * 64,
        configuration_digest="6" * 64,
        released_at=RELEASED_AT,
    )


def test_base_component_projection_carries_owner_scope() -> None:
    base = _base()
    assert base.tenant_record_id == TENANT
    assert base.validity_study_id == STUDY
    assert _canonical_base_evidence(base) == base


def test_adjustment_component_projection_carries_owner_scope() -> None:
    adjustment = _adjustment()
    assert adjustment.tenant_record_id == TENANT
    assert adjustment.validity_study_id == STUDY
    assert _canonical_adjustment_evidence(adjustment) == adjustment


def test_base_component_hidden_scope_structure_fails_closed() -> None:
    forged = tuple.__new__(BaseWeightComponentEvidence, tuple(_base()) + ("hidden-scope",))
    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match="non-canonical"):
        _canonical_base_evidence(forged)


def test_adjustment_component_hidden_scope_structure_fails_closed() -> None:
    forged = tuple.__new__(AdjustmentComponentEvidence, tuple(_adjustment()) + ("hidden-scope",))
    with pytest.raises(FinalWeightComponentEvidenceIntegrityError, match="non-canonical"):
        _canonical_adjustment_evidence(forged)
