"""Regression coverage for value-free selection-review reason metadata."""

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from orgmetra_selection_review import build_selection_review_packet


def _build(reason_code: str = "candidate_assessment"):
    """Build a valid high-impact selection-review packet while varying its reason."""
    return build_selection_review_packet(
        tenant_record_id="2b37b937-c3f1-49aa-8d19-785a7b7a9917",
        candidate_reference="candidate_profile:11111111-1111-4111-8111-111111111111",
        job_profile_reference="job_profile:22222222-2222-4222-8222-222222222222",
        decision_evidence_set_reference="decision_evidence_set:33333333-3333-4333-8333-333333333333",
        evidence_set_digest="0" * 64,
        reviewer_actor_reference="actor:44444444-4444-4444-8444-444444444444",
        purpose_code="selection_review",
        reason_code=reason_code,
        evidence_version_code="evidence_version_1",
        generated_at=datetime(2026, 8, 19, 8, 50, tzinfo=timezone.utc),
    )


@pytest.mark.parametrize(
    "reason_code",
    ["jane_doe", "salary_120000", "race_gender", "remote_two_days"],
)
def test_rejects_value_bearing_or_ungoverned_reason_codes(reason_code: str) -> None:
    """Prevent the reason field from becoming a candidate/value side channel."""
    with pytest.raises(ValueError, match="authorized selection-review reason"):
        _build(reason_code)


def test_replace_cannot_bypass_closed_reason_vocabulary() -> None:
    """Mutation-by-copy must revalidate the reviewed reason vocabulary."""
    with pytest.raises(ValueError, match="authorized selection-review reason"):
        replace(_build(), reason_code="candidate_jane_doe")
