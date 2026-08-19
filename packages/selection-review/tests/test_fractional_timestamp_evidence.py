from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

from orgmetra_selection_review import build_selection_review_packet


def _build():
    return build_selection_review_packet(
        tenant_record_id="11111111-1111-4111-8111-111111111111",
        candidate_reference="candidate_profile:candidate-001",
        job_profile_reference="job_profile:job-001",
        decision_evidence_set_reference="decision_evidence_set:evidence-001",
        evidence_set_digest="a" * 64,
        reviewer_actor_reference="actor:reviewer-001",
        purpose_code="selection_review",
        reason_code="structured_selection_review",
        evidence_version_code="evidence_version_1",
        generated_at=datetime(2026, 8, 19, 2, 20, 0, 123456, tzinfo=timezone.utc),
    )


def test_fractional_seconds_remain_distinct_selection_evidence() -> None:
    first = _build()
    second = replace(first, generated_at=first.generated_at + timedelta(microseconds=1))

    assert "2026-08-19T02:20:00.123456Z" in first.canonical_json()
    assert "2026-08-19T02:20:00.123457Z" in second.canonical_json()
    assert first.canonical_json() != second.canonical_json()
    assert first.sha256_digest() != second.sha256_digest()
