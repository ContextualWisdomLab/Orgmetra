"""Recorded-time integrity regressions for high-impact selection evidence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from orgmetra_selection_review import build_selection_review_packet


class _ForgedRecordedTime(datetime):
    """Attempt to forge canonical evidence through datetime subclass methods."""

    def astimezone(self, tz=None):  # noqa: ANN001
        """Preserve the hostile runtime type through UTC normalization."""
        return self

    def isoformat(self, sep="T", timespec="auto") -> str:  # noqa: ARG002
        """Render a different instant from the underlying datetime value."""
        return "2099-01-01T00:00:00+00:00"


def test_selection_review_rejects_datetime_subclasses_before_canonicalization() -> None:
    """Do not let caller-controlled datetime methods rewrite immutable review evidence."""
    forged = _ForgedRecordedTime(2026, 8, 21, 4, 45, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="generated_at must be an exact timezone-aware datetime"):
        build_selection_review_packet(
            tenant_record_id="11111111-1111-4111-8111-111111111111",
            candidate_reference="candidate_profile:22222222-2222-4222-8222-222222222222",
            job_profile_reference="job_profile:33333333-3333-4333-8333-333333333333",
            decision_evidence_set_reference="decision_evidence_set:44444444-4444-4444-8444-444444444444",
            evidence_set_digest="a" * 64,
            reviewer_actor_reference="actor:55555555-5555-4555-8555-555555555555",
            purpose_code="selection_review",
            reason_code="candidate_assessment",
            evidence_version_code="evidence_version_1",
            generated_at=forged,
        )


@pytest.mark.parametrize(
    "generated_at",
    [
        datetime.min.replace(tzinfo=timezone(timedelta(hours=1))),
        datetime.max.replace(tzinfo=timezone(-timedelta(hours=1))),
    ],
)
def test_selection_review_normalizes_unrepresentable_utc_overflow(
    generated_at: datetime,
) -> None:
    """Normalize out-of-range UTC conversion into the packet's boundary error."""
    with pytest.raises(ValueError, match="generated_at"):
        build_selection_review_packet(
            tenant_record_id="11111111-1111-4111-8111-111111111111",
            candidate_reference="candidate_profile:22222222-2222-4222-8222-222222222222",
            job_profile_reference="job_profile:33333333-3333-4333-8333-333333333333",
            decision_evidence_set_reference="decision_evidence_set:44444444-4444-4444-8444-444444444444",
            evidence_set_digest="a" * 64,
            reviewer_actor_reference="actor:55555555-5555-4555-8555-555555555555",
            purpose_code="selection_review",
            reason_code="candidate_assessment",
            evidence_version_code="evidence_version_1",
            generated_at=generated_at,
        )
