"""Regression coverage for creation-bound audit canonical evidence."""

from datetime import datetime, timezone
from uuid import UUID

import pytest

from orgmetra_hris_kernel import audit as audit_module
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


def test_post_init_reentry_cannot_reseal_valid_mutated_evidence() -> None:
    """Re-entering initialization cannot replace the creation-bound audit truth."""
    event = _event()
    original_snapshot = audit_module._AUDIT_CREATION_SNAPSHOTS[id(event)]
    object.__setattr__(event, "reason_code", "manager_transfer")

    with pytest.raises(ValueError, match="already issued"):
        event.__post_init__()

    assert audit_module._AUDIT_CREATION_SNAPSHOTS[id(event)] is original_snapshot
    with pytest.raises(ValueError, match="creation-time audit evidence"):
        event.canonical_json()


def test_missing_creation_snapshot_does_not_restore_issuance_eligibility() -> None:
    """Losing the snapshot cannot let one live event issue a replacement snapshot."""
    event = _event()
    audit_module._AUDIT_CREATION_SNAPSHOTS.pop(id(event))

    with pytest.raises(ValueError, match="already issued"):
        event.__post_init__()

    assert id(event) not in audit_module._AUDIT_CREATION_SNAPSHOTS


def test_event_has_no_mutable_instance_slot_for_creation_seal() -> None:
    """Low-level event mutation cannot rewrite the module-owned issuance proof."""
    event = _event()

    assert not hasattr(event, "_creation_snapshot")
    with pytest.raises(AttributeError):
        object.__setattr__(event, "_creation_snapshot", ())


def test_canonical_export_fails_closed_when_issuance_proof_is_missing() -> None:
    """Missing process-local issuance evidence cannot silently mint a canonical event."""
    event = _event()
    audit_module._AUDIT_CREATION_SNAPSHOTS.pop(id(event))

    with pytest.raises(ValueError, match="creation-time audit evidence is unavailable"):
        event.canonical_json()


@pytest.mark.parametrize("corrupt_snapshot", [[], tuple(range(12))])
def test_canonical_export_rejects_malformed_issuance_proof(corrupt_snapshot: object) -> None:
    """Malformed module-owned issuance state fails closed before evidence comparison."""
    event = _event()
    audit_module._AUDIT_CREATION_SNAPSHOTS[id(event)] = corrupt_snapshot  # type: ignore[assignment]

    with pytest.raises(ValueError, match="creation-time audit evidence is unavailable"):
        event.canonical_json()
