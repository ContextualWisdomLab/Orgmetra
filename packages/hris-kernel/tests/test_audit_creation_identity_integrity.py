"""Regression coverage for creation-bound audit canonical evidence."""

from datetime import datetime, timezone
import gc
from uuid import UUID

import pytest

from orgmetra_hris_kernel import audit as audit_module
from orgmetra_hris_kernel.audit import AuditOutboxEvent


def _event_values() -> dict[str, object]:
    """Return one valid high-impact audit event payload with stable opaque evidence."""
    return {
        "event_id": UUID("00000000-0000-4000-8000-000000000002"),
        "tenant_record_id": UUID("00000000-0000-4000-8000-000000000001"),
        "source_service": "people_core",
        "event_type": "orgmetra.people.assignment.recorded",
        "resource_reference": "assignment_record:01JTESTOPAQUE",
        "actor_reference": "keyverse_subject:01JACTOROPAQUE",
        "purpose_code": "workforce_administration",
        "reason_code": "hire_completion",
        "evidence_version_code": "employment-offer:v3",
        "result_code": "recorded",
        "occurred_at": datetime(2026, 8, 17, 1, 30, tzinfo=timezone.utc),
        "high_impact": True,
        "confirmation_reference": "confirmation:01JCONFIRMOPAQUE",
    }


def _event() -> AuditOutboxEvent:
    """Build one valid high-impact audit event with stable opaque evidence."""
    return AuditOutboxEvent(**_event_values())  # type: ignore[arg-type]


def _unissued_event() -> AuditOutboxEvent:
    """Populate an exact event object without running its governed issuance hook."""
    event = object.__new__(AuditOutboxEvent)
    for field_name, value in _event_values().items():
        object.__setattr__(event, field_name, value)
    return event


def _creation_snapshot(event: AuditOutboxEvent) -> tuple[object, ...]:
    """Capture the same exact inert values accepted by the private runtime."""
    return audit_module._event_snapshot(
        event_id=event.event_id,
        tenant_record_id=event.tenant_record_id,
        source_service=event.source_service,
        event_type=event.event_type,
        resource_reference=event.resource_reference,
        actor_reference=event.actor_reference,
        purpose_code=event.purpose_code,
        reason_code=event.reason_code,
        evidence_version_code=event.evidence_version_code,
        result_code=event.result_code,
        occurred_at=event.occurred_at,
        high_impact=event.high_impact,
        confirmation_reference=event.confirmation_reference,
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
    original = event.canonical_json()
    object.__setattr__(event, "reason_code", "manager_transfer")

    with pytest.raises(ValueError, match="already issued"):
        event.__post_init__()

    with pytest.raises(ValueError, match="creation-time audit evidence"):
        event.canonical_json()
    assert "manager_transfer" not in original


def test_unissued_exact_event_cannot_export_canonical_evidence() -> None:
    """Low-level field population cannot substitute for the governed issuance lifecycle."""
    event = _unissued_event()

    with pytest.raises(ValueError, match="creation-time audit evidence is unavailable"):
        event.canonical_json()


def test_event_lifetime_cleanup_releases_private_runtime_state() -> None:
    """The closure-private runtime releases its snapshot when the claimed object dies."""
    claim, record, lookup = audit_module._build_audit_creation_runtime()
    event = _event()
    event_identity, identity_marker = claim(event)
    snapshot = _creation_snapshot(event)
    record(event_identity, identity_marker, snapshot)

    assert lookup(event_identity) is snapshot

    del event
    gc.collect()

    assert lookup(event_identity) is None


def test_stale_finalizer_marker_cannot_clear_reused_identity_state() -> None:
    """A stale lifetime callback cannot delete evidence registered by a replacement identity."""
    event_identity = -1
    stale_marker = object()
    replacement_marker = object()
    replacement_snapshot = ("replacement",)
    live_issuances = {event_identity: replacement_marker}
    creation_snapshots = {event_identity: replacement_snapshot}

    audit_module._clear_audit_creation_state(
        live_issuances,
        creation_snapshots,
        event_identity,
        stale_marker,
    )

    assert live_issuances[event_identity] is replacement_marker
    assert creation_snapshots[event_identity] is replacement_snapshot


def test_event_has_no_mutable_instance_slot_for_creation_seal() -> None:
    """Low-level event mutation cannot rewrite the module-owned issuance proof."""
    event = _event()

    assert not hasattr(event, "_creation_snapshot")
    with pytest.raises(AttributeError):
        object.__setattr__(event, "_creation_snapshot", ())


@pytest.mark.parametrize("corrupt_snapshot", [[], tuple(range(12))])
def test_creation_snapshot_validator_rejects_malformed_private_evidence(
    corrupt_snapshot: object,
) -> None:
    """Malformed private issuance evidence fails closed before value comparison."""
    with pytest.raises(ValueError, match="creation-time audit evidence is unavailable"):
        audit_module._validate_creation_snapshot(corrupt_snapshot)
