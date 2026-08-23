"""Regression for system-recorded issuance chronology."""

from datetime import date, datetime, timezone

import pytest

from orgmetra_organization_hierarchy_change_review import (
    build_organization_hierarchy_change_review_packet,
)


def test_rejects_future_system_recorded_time() -> None:
    """Do not seal hierarchy-review evidence for a system time that has not occurred."""
    with pytest.raises(ValueError, match="recorded_at must not be in the future"):
        build_organization_hierarchy_change_review_packet(
            tenant_record_id="0195c23d-9f00-7000-8000-000000000001",
            organization_hierarchy_change_reference=(
                "organization_hierarchy_change:11111111-1111-4111-8111-111111111111"
            ),
            organization_unit_reference=(
                "organization_unit:0195c23d-9f00-7000-8000-000000000002"
            ),
            current_parent_organization_unit_reference=(
                "organization_unit:0195c23d-9f00-7000-8000-000000000003"
            ),
            proposed_parent_organization_unit_reference=(
                "organization_unit:0195c23d-9f00-7000-8000-000000000004"
            ),
            effective_on=date(2099, 1, 2),
            organization_unit_snapshot_digest="a" * 64,
            hierarchy_snapshot_digest="b" * 64,
            requester_reference="actor:22222222-2222-4222-8222-222222222222",
            reviewer_reference="actor:33333333-3333-4333-8333-333333333333",
            purpose_code="organization_hierarchy_change_review",
            reason_code="organizational_realignment",
            recorded_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
        )
