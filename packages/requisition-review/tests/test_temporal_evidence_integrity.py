"""Recorded-time integrity regressions for requisition-review evidence."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from orgmetra_requisition_review import build_requisition_review_packet


class _ForgedGeneratedAt(datetime):
    """Attempt to forge canonical evidence through datetime subclass methods."""

    def astimezone(self, tz=None):  # noqa: ANN001
        """Preserve the hostile runtime type through UTC normalization."""
        return self

    def isoformat(self, sep="T", timespec="auto") -> str:  # noqa: ARG002
        """Render a different instant from the underlying datetime value."""
        return "2099-01-01T00:00:00+00:00"


def test_requisition_review_rejects_datetime_subclasses_before_canonicalization() -> None:
    """Do not let caller-controlled datetime methods rewrite approval evidence."""
    forged = _ForgedGeneratedAt(2026, 8, 21, 5, 10, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="generated_at must be an exact timezone-aware datetime"):
        build_requisition_review_packet(
            tenant_record_id="2b37b937-c3f1-49aa-8d19-785a7b7a9917",
            requisition_reference="requisition:11111111-1111-4111-8111-111111111111",
            job_profile_reference="job_profile:22222222-2222-4222-8222-222222222222",
            job_requirements_reference="job_requirements:33333333-3333-4333-8333-333333333333",
            job_requirements_digest="0" * 64,
            requirements_version_code="requirements_version_1",
            headcount_authorization_reference="headcount_authorization:44444444-4444-4444-8444-444444444444",
            hiring_manager_actor_reference="actor:55555555-5555-4555-8555-555555555555",
            approver_actor_reference="actor:66666666-6666-4666-8666-666666666666",
            requested_opening_count=3,
            purpose_code="requisition_review",
            reason_code="approved_growth_plan",
            generated_at=forged,
        )
