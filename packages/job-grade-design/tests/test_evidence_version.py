"""Regression contract for explicit Job-grade review evidence versioning."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from orgmetra_job_grade_design import build_job_grade_design_review_packet


def packet_values() -> dict[str, object]:
    """Return one complete valid versioned Job-grade review input."""
    return {
        "tenant_record_id": "0198f1c0-7d6e-7f10-8a41-b1d9e2fe0199",
        "job_record_reference": f"job_record:{uuid4()}",
        "job_analysis_snapshot_reference": f"job_analysis_snapshot:{uuid4()}",
        "job_analysis_snapshot_digest": "a" * 64,
        "job_evaluation_method_code": "factor_based_job_evaluation",
        "job_evaluation_method_digest": "b" * 64,
        "grade_code": "G07",
        "band_code": "P3",
        "grade_band_definition_digest": "c" * 64,
        "requester_actor_reference": f"actor:{uuid4()}",
        "reviewer_actor_reference": f"actor:{uuid4()}",
        "reason_code": "job_architecture_alignment",
        "evidence_version": 1,
        "reviewed_at": datetime(2026, 8, 24, 8, 0, tzinfo=timezone.utc),
        "recorded_at": datetime(2026, 8, 24, 8, 1, tzinfo=timezone.utc),
    }


def test_canonical_job_grade_review_binds_explicit_evidence_version() -> None:
    """Durable audit evidence must carry the reviewed contract version it represents."""
    packet = build_job_grade_design_review_packet(**packet_values())

    assert packet.evidence_version == 1
    assert packet.canonical_document()["evidence_version"] == 1


@pytest.mark.parametrize("value", [0, -1, 2_147_483_648, True, 1.0, "1"])
def test_rejects_invalid_or_non_exact_evidence_versions(value: object) -> None:
    """Evidence version must be exactly built-in integer 1, never bool/coercible data."""
    data = packet_values()
    data["evidence_version"] = value

    with pytest.raises(ValueError, match="evidence_version"):
        build_job_grade_design_review_packet(**data)
