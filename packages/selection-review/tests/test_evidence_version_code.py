"""Regression coverage for canonical, value-free selection-review evidence versions."""

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from orgmetra_selection_review import build_selection_review_packet


def _build(evidence_version_code: str = "evidence_version_1"):
    """Build a valid selection-review packet while varying only its evidence version."""
    return build_selection_review_packet(
        tenant_record_id="2b37b937-c3f1-49aa-8d19-785a7b7a9917",
        candidate_reference="candidate_profile:11111111-1111-4111-8111-111111111111",
        job_profile_reference="job_profile:22222222-2222-4222-8222-222222222222",
        decision_evidence_set_reference="decision_evidence_set:33333333-3333-4333-8333-333333333333",
        evidence_set_digest="0" * 64,
        reviewer_actor_reference="actor:44444444-4444-4444-8444-444444444444",
        purpose_code="selection_review",
        reason_code="candidate_assessment",
        evidence_version_code=evidence_version_code,
        generated_at=datetime(2026, 8, 19, 9, 10, tzinfo=timezone.utc),
    )


@pytest.mark.parametrize(
    "evidence_version_code",
    [
        "evidence_version_jane_doe",
        "evidence_version_salary_120000",
        "evidence_version_race_gender",
        "evidence_version_remote_two_days",
        "evidence_version_0",
        "evidence_version_01",
        "evidence_version_2147483648",
    ],
)
def test_rejects_value_bearing_or_noncanonical_evidence_version_codes(
    evidence_version_code: str,
) -> None:
    """Prevent evidence-version metadata from becoming a candidate/value side channel."""
    with pytest.raises(ValueError, match="canonical positive evidence version"):
        _build(evidence_version_code)


def test_accepts_bounded_canonical_evidence_versions() -> None:
    """Accept canonical positive versions through the supported signed-int32 ceiling."""
    assert _build("evidence_version_1").evidence_version_code == "evidence_version_1"
    assert (
        _build("evidence_version_2147483647").evidence_version_code
        == "evidence_version_2147483647"
    )


def test_replace_cannot_bypass_evidence_version_validation() -> None:
    """Mutation-by-copy must revalidate the canonical evidence-version contract."""
    with pytest.raises(ValueError, match="canonical positive evidence version"):
        replace(_build(), evidence_version_code="evidence_version_jane_doe")
