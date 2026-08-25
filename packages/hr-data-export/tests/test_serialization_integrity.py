"""Serialization-time integrity regressions for HR data export review evidence."""

from datetime import datetime, timedelta, timezone

import pytest

from orgmetra_hr_data_export import HrDataExportReviewPacket


def _packet() -> HrDataExportReviewPacket:
    """Return one valid packet whose timestamp is frozen to UTC at construction."""
    return HrDataExportReviewPacket(
        tenant_record_id="0198d2dd-7215-7c44-a8a3-7d4d42b9087e",
        export_review_reference="export_review:3f66ab91-2d1d-4a16-a37b-a9a897382692",
        resource_kind="person_record",
        resource_reference="person_record:431d7f42-720b-4d58-bdab-2af689089a43",
        authorization_evidence_reference=(
            "authorization_decision:29fde057-7f82-4aaa-a906-e31445b05a0b"
        ),
        authorization_evidence_digest="7" * 64,
        authorization_policy_version_code="people_export_policy_v1",
        requester_reference="actor:30d0887a-acf9-4b33-b19f-71d5015b5c6e",
        reviewer_reference="actor:e296fc39-0b2a-48ce-b53a-a7a814cbb0a9",
        purpose_code="hr_data_export_review",
        reason_code="employee_access_request",
        requested_fields=("business_email_address", "display_name"),
        export_format_code="json",
        destination_kind="authenticated_one_time_download",
        generated_at=datetime(2026, 8, 22, 13, 0, tzinfo=timezone(timedelta(hours=9))),
    )


def test_canonicalization_rejects_reinjected_non_utc_timestamp() -> None:
    """Low-level mutation cannot reintroduce a different timezone representation."""
    result = _packet()
    object.__setattr__(
        result,
        "generated_at",
        datetime(2026, 8, 22, 13, 0, tzinfo=timezone(timedelta(hours=9))),
    )
    with pytest.raises(ValueError, match="canonical built-in UTC"):
        result.canonical_json()


def test_canonicalization_rejects_valid_post_issuance_field_scope_rewrite() -> None:
    """A valid-looking field-scope rewrite cannot become a second reviewed audit truth."""
    result = _packet()
    original_digest = result.sha256_digest()
    object.__setattr__(result, "requested_fields", ("display_name",))

    with pytest.raises(ValueError, match="altered after issuance"):
        result.canonical_json()
    assert original_digest != "0" * 64
