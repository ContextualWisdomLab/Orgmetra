"""Regression coverage for offer-approval recorded-time evidence integrity."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from orgmetra_offer_approval import build_offer_approval_packet


class ForgedDateTime(datetime):
    """Datetime subclass able to forge canonical high-impact approval evidence."""

    def astimezone(self, tz=None):  # type: ignore[no-untyped-def]
        """Keep the hostile subclass alive across UTC normalization."""
        return self

    def isoformat(self, *args, **kwargs) -> str:  # type: ignore[no-untyped-def]
        """Return an instant different from the underlying approval evidence."""
        return "2099-12-31T23:59:59+00:00"


def test_rejects_datetime_subclass_that_can_forge_generated_at() -> None:
    """Canonical offer evidence must not invoke caller-overridable datetime methods."""
    with pytest.raises(ValueError, match="generated_at"):
        build_offer_approval_packet(
            tenant_record_id="11111111-1111-4111-8111-111111111111",
            offer_approval_reference="offer_approval:10000000-0000-4000-8000-000000000001",
            candidate_profile_reference="candidate_profile:10000000-0000-4000-8000-000000000002",
            requisition_reference="requisition:10000000-0000-4000-8000-000000000003",
            job_profile_reference="job_profile:10000000-0000-4000-8000-000000000004",
            position_record_reference="position_record:10000000-0000-4000-8000-000000000005",
            selection_decision_reference="selection_decision:10000000-0000-4000-8000-000000000006",
            selection_decision_digest="a" * 64,
            compensation_package_reference="compensation_package:10000000-0000-4000-8000-000000000007",
            compensation_package_digest="b" * 64,
            offer_terms_reference="offer_terms:10000000-0000-4000-8000-000000000008",
            offer_terms_digest="c" * 64,
            requester_reference="actor:10000000-0000-4000-8000-000000000009",
            approver_reference="actor:10000000-0000-4000-8000-00000000000a",
            purpose_code="offer_approval_review",
            reason_code="selected_candidate_offer_review",
            generated_at=ForgedDateTime(2026, 8, 21, 4, 50, tzinfo=timezone.utc),
        )
