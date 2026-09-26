"""Issuance-time freshness regression for reporting-change review evidence."""

from datetime import date, datetime, timedelta, timezone

import pytest

from orgmetra_position_reporting_change_review import build_position_reporting_change_review_packet


def test_rejects_future_system_recorded_time() -> None:
    """Do not issue review evidence with a system-recorded instant that has not occurred."""
    with pytest.raises(ValueError, match="recorded_at must not be in the future"):
        build_position_reporting_change_review_packet(
            tenant_record_id="0195c23d-9f00-7000-8000-000000000001",
            position_reporting_change_reference=(
                "position_reporting_change:11111111-1111-4111-8111-111111111111"
            ),
            subordinate_position_reference="position_record:0195c23d-9f00-7000-8000-000000000002",
            current_manager_position_reference="position_record:0195c23d-9f00-7000-8000-000000000003",
            proposed_manager_position_reference="position_record:0195c23d-9f00-7000-8000-000000000004",
            effective_on=date(2026, 9, 1),
            position_scope_snapshot_digest="a" * 64,
            organization_scope_snapshot_digest="b" * 64,
            requester_reference="actor:22222222-2222-4222-8222-222222222222",
            reviewer_reference="actor:33333333-3333-4333-8333-333333333333",
            purpose_code="position_reporting_change_review",
            reason_code="organizational_realignment",
            recorded_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
