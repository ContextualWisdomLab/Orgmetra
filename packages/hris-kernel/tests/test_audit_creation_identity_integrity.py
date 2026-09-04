"""Regression coverage for creation-bound audit canonical evidence."""

from datetime import datetime, timezone
from uuid import UUID

import pytest

from orgmetra_hris_kernel.audit import AuditOutboxEvent


def _event() -> AuditOutboxEvent:
    """Build one valid high-impact audit event with stable opaque evidence."""
    return AuditOutboxEvent(
        event_id=UUID("00000000-0000-4000-8000-000000000002"),
        tenant_record_id=UUID("00000000-0000-4000-8000-000000000001"),
        source_service="people_core",
        event_type="orgmetra.people.assignment.recorded",
        resource_reference="assignment_record:01JTESTOPAQUE",
        actor_reference="keyverse_subject:01JACTOROPAQUE",
        purpose_code="workforce_administration",
        reason_code="hire_completion",
        evidence_version_code="employment-offer:v3",
        result_code="recorded",
        occurred_at=datetime(2026, 8, 17, 1, 30, tzinfo=timezone.utc),
        high_impact=True,
        confirmation_reference="confirmation:01JCONFIRMOPAQUE",
    )


@pytest.mark.parametrize(
    ("field_name", "replacement"),
    [
        ("actor_reference", "keyverse_subject:01JOTHERACTOR"),
        ("reason_code", "manager_transfer"),
        ("result_code", "updated"),
        ("confirmation_reference", "confirmation:01JOTHERCONFIRM"),
    ],
)
def test_valid_post_construction_replacement_cannot_reissue_canonical_evidence(
    field_name: str,
    replacement: str,
) -> None:
    """A live event cannot mint a second valid canonical truth after issuance."""
    event = _event()
    original = event.canonical_json()
    object.__setattr__(event, field_name, replacement)

    with pytest.raises(ValueError, match="creation-time audit evidence"):
        event.canonical_json()

    assert replacement not in original
