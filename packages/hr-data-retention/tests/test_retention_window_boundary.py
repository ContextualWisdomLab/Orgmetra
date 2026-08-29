"""Boundary regression for the reviewed HR retention window."""

from datetime import date, datetime, timezone

from orgmetra_hr_data_retention import HrDataRetentionReviewPacket


def test_review_on_the_due_date_still_requires_retention() -> None:
    """Treat the exact reviewed due date as retained, not disposition-review eligible."""
    review = HrDataRetentionReviewPacket(
        tenant_record_id="0198f0a1-7b2c-7abc-8def-0123456789ab",
        retention_review_reference="retention_review:550e8400-e29b-41d4-a716-446655440003",
        resource_kind="candidate_profile",
        resource_reference="candidate_profile:550e8400-e29b-41d4-a716-446655440000",
        record_category_code="candidate_employment_record",
        retention_policy_reference="retention_policy:550e8400-e29b-41d4-a716-446655440001",
        retention_policy_digest="a" * 64,
        retention_due_on=date(2025, 8, 31),
        reviewed_on=date(2025, 8, 31),
        legal_hold_state="clear",
        legal_hold_reference=None,
        legal_hold_digest=None,
        requester_actor_reference="actor:550e8400-e29b-41d4-a716-446655440002",
        reviewer_actor_reference="actor:550e8400-e29b-41d4-a716-446655440005",
        evidence_version=1,
        recorded_at=datetime(2025, 8, 31, 6, 0, tzinfo=timezone.utc),
    )
    assert review.retention_window_state == "retain_until_due"
    assert review.disposition_authorization_state == "not_authorized_to_delete"
