"""Regression for transitive hierarchy-review validation authority."""

from datetime import date, datetime, timezone

import pytest

import orgmetra_organization_hierarchy_change_review.review as review_module
from orgmetra_organization_hierarchy_change_review import (
    build_organization_hierarchy_change_review_packet,
)


def test_issuance_does_not_trust_mutable_transitive_reference_validator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject invalid references even if a transitive module helper is replaced."""
    monkeypatch.setattr(review_module, "_validate_reference", lambda *args, **kwargs: None)

    with pytest.raises(ValueError, match="organization_unit_reference must be a canonical"):
        build_organization_hierarchy_change_review_packet(
            tenant_record_id="0195c23d-9f00-7000-8000-000000000001",
            organization_hierarchy_change_reference=(
                "organization_hierarchy_change:66666666-6666-4666-8666-666666666666"
            ),
            organization_unit_reference="organization_unit:not-a-uuid",
            current_parent_organization_unit_reference=(
                "organization_unit:0195c23d-9f00-7000-8000-000000000003"
            ),
            proposed_parent_organization_unit_reference=(
                "organization_unit:0195c23d-9f00-7000-8000-000000000004"
            ),
            effective_on=date(2026, 9, 1),
            organization_unit_snapshot_digest="a" * 64,
            hierarchy_snapshot_digest="b" * 64,
            requester_reference="actor:22222222-2222-4222-8222-222222222222",
            reviewer_reference="actor:33333333-3333-4333-8333-333333333333",
            purpose_code="organization_hierarchy_change_review",
            reason_code="organizational_realignment",
            recorded_at=datetime(2026, 8, 23, 7, 0, tzinfo=timezone.utc),
        )
