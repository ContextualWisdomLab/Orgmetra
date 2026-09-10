"""Regression for packet-level checked-versus-emitted runtime substitution."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import fields
from datetime import date, datetime, timezone
import sys
from threading import Event
from uuid import uuid4

import pytest

import orgmetra_organization_hierarchy_change_review.review as review_module
from orgmetra_organization_hierarchy_change_review import (
    OrganizationHierarchyChangeReviewPacket,
    build_organization_hierarchy_change_review_packet,
)


def _tenant_swap_getattribute(self: object, name: str) -> object:
    """Model a subclass that would swap tenant evidence across repeated reads."""
    if name == "tenant_record_id":
        return "not-a-uuid"
    return object.__getattribute__(self, name)


def _no_op_post_init(self: object) -> None:
    """Model a subclass that would suppress the inherited post-init validator."""
    return None


def test_rejects_packet_runtime_subclass_before_trust_field_validation() -> None:
    """Do not let packet polymorphism reach validation or canonical emission."""
    with pytest.raises(TypeError, match="does not support caller-defined subclasses"):
        type(
            "TenantSwapPacket",
            (OrganizationHierarchyChangeReviewPacket,),
            {"__getattribute__": _tenant_swap_getattribute},
        )


def test_rejects_subclass_that_bypasses_base_post_init() -> None:
    """A subclass must not suppress the base validation hook entirely."""
    with pytest.raises(TypeError, match="does not support caller-defined subclasses"):
        type(
            "PostInitBypassPacket",
            (OrganizationHierarchyChangeReviewPacket,),
            {"__post_init__": _no_op_post_init},
        )


class _ForgedText(str):
    """Retain caller-owned behavior while preserving serialized text."""


class _ForgedInt(int):
    """Retain caller-owned behavior while preserving serialized integer value."""


def _build_packet() -> OrganizationHierarchyChangeReviewPacket:
    """Build one isolated valid packet for post-issuance substitution tests."""
    return build_organization_hierarchy_change_review_packet(
        tenant_record_id="0195c23d-9f00-7000-8000-000000000001",
        organization_hierarchy_change_reference=f"organization_hierarchy_change:{uuid4()}",
        organization_unit_reference="organization_unit:0195c23d-9f00-7000-8000-000000000002",
        current_parent_organization_unit_reference="organization_unit:0195c23d-9f00-7000-8000-000000000003",
        proposed_parent_organization_unit_reference="organization_unit:0195c23d-9f00-7000-8000-000000000004",
        effective_on=date(2026, 9, 1),
        organization_unit_snapshot_digest="a" * 64,
        hierarchy_snapshot_digest="b" * 64,
        requester_reference="actor:22222222-2222-4222-8222-222222222222",
        reviewer_reference="actor:33333333-3333-4333-8333-333333333333",
        purpose_code="organization_hierarchy_change_review",
        reason_code="organizational_realignment",
        recorded_at=datetime(2026, 8, 23, 7, 0, tzinfo=timezone.utc),
    )


def _issue_after_snapshot_capture(
    packet: OrganizationHierarchyChangeReviewPacket,
    snapshot_captured: Event,
    release_snapshot: Event,
) -> None:
    """Pause issuance after its snapshot exists without replacing trusted validator bindings."""

    def trace_validator_call(frame: object, event: str, _arg: object) -> object:
        if getattr(frame, "f_code", None).co_name == "_validate_issuance_snapshot" and event == "call":
            snapshot_captured.set()
            if not release_snapshot.wait(timeout=5):
                raise AssertionError("test did not release captured issuance snapshot")
        return trace_validator_call

    sys.settrace(trace_validator_call)
    try:
        packet.__post_init__()
    finally:
        sys.settrace(None)


@pytest.mark.parametrize(
    ("field_name", "forged_value"),
    [
        ("reason_code", _ForgedText("organizational_realignment")),
        ("evidence_version", _ForgedInt(1)),
    ],
)
def test_rejects_representation_preserving_runtime_substitution_after_issuance(
    field_name: str,
    forged_value: object,
) -> None:
    """Reject caller-owned scalar behavior even when canonical bytes would stay identical."""
    packet = _build_packet()
    object.__setattr__(packet, field_name, forged_value)
    with pytest.raises(ValueError, match="runtime types changed after issuance|evidence changed after issuance"):
        packet.canonical_json()


def test_rejects_manual_reissuance_after_reference_retargeting() -> None:
    """An issued packet cannot be resealed under a new reference by calling its hook again."""
    packet = _build_packet()
    object.__setattr__(
        packet,
        "organization_hierarchy_change_reference",
        f"organization_hierarchy_change:{uuid4()}",
    )
    object.__setattr__(packet, "reason_code", "administrative_correction")

    with pytest.raises(ValueError, match="may be issued only once"):
        packet.__post_init__()
    with pytest.raises(ValueError, match="evidence changed after issuance"):
        packet.canonical_json()


@pytest.mark.parametrize(
    "registry_name",
    [
        "_CREATION_DIGESTS",
        "_ISSUANCE_IN_PROGRESS",
        "_LIVE_REFERENCE_BINDINGS",
        "_PACKET_BINDINGS",
    ],
)
def test_module_exposes_no_mutable_issuance_registry_capability(registry_name: str) -> None:
    """Ordinary module consumers must not receive direct mutation handles to issuance state."""
    assert registry_name not in vars(review_module)


def test_rejects_concurrent_reissuance_while_initial_issuance_is_in_progress() -> None:
    """A second issuance call must fail while the first call owns the issuance reservation."""
    template = _build_packet()
    packet = object.__new__(OrganizationHierarchyChangeReviewPacket)
    for field in fields(OrganizationHierarchyChangeReviewPacket):
        object.__setattr__(packet, field.name, object.__getattribute__(template, field.name))
    object.__setattr__(
        packet,
        "organization_hierarchy_change_reference",
        f"organization_hierarchy_change:{uuid4()}",
    )

    snapshot_captured = Event()
    release_snapshot = Event()
    with ThreadPoolExecutor(max_workers=1) as executor:
        issuance = executor.submit(
            _issue_after_snapshot_capture,
            packet,
            snapshot_captured,
            release_snapshot,
        )
        assert snapshot_captured.wait(timeout=5)
        with pytest.raises(ValueError, match="may be issued only once"):
            packet.__post_init__()
        release_snapshot.set()
        issuance.result(timeout=5)

    assert packet.canonical_json()


def test_canonical_export_validates_and_emits_one_snapshot_during_concurrent_mutation() -> None:
    """A mutation after direct export snapshot capture cannot change that export."""
    packet = _build_packet()
    expected_json = packet.canonical_json()
    snapshot_captured = Event()
    release_snapshot = Event()

    def trace_snapshot_return(frame: object, event: str, _arg: object) -> object:
        if getattr(frame, "f_code", None).co_name == "capture_state" and event == "return":
            snapshot_captured.set()
            if not release_snapshot.wait(timeout=5):
                raise AssertionError("test did not release captured export snapshot")
        return trace_snapshot_return

    def export_after_trace_install() -> str:
        sys.settrace(trace_snapshot_return)
        try:
            return packet.canonical_json()
        finally:
            sys.settrace(None)

    with ThreadPoolExecutor(max_workers=1) as executor:
        export = executor.submit(export_after_trace_install)
        assert snapshot_captured.wait(timeout=5)
        object.__setattr__(packet, "reason_code", "administrative_correction")
        release_snapshot.set()
        assert export.result(timeout=5) == expected_json

    with pytest.raises(ValueError, match="evidence changed after issuance"):
        packet.canonical_json()


def test_issuance_validates_and_seals_one_snapshot_during_concurrent_mutation() -> None:
    """Never seal an after-snapshot mutation as though that value were reviewed."""
    template = _build_packet()
    packet = object.__new__(OrganizationHierarchyChangeReviewPacket)
    for field in fields(OrganizationHierarchyChangeReviewPacket):
        object.__setattr__(packet, field.name, object.__getattribute__(template, field.name))
    object.__setattr__(
        packet,
        "organization_hierarchy_change_reference",
        f"organization_hierarchy_change:{uuid4()}",
    )

    snapshot_captured = Event()
    release_snapshot = Event()
    with ThreadPoolExecutor(max_workers=1) as executor:
        issuance = executor.submit(
            _issue_after_snapshot_capture,
            packet,
            snapshot_captured,
            release_snapshot,
        )
        assert snapshot_captured.wait(timeout=5)
        object.__setattr__(packet, "reason_code", "unreviewed_override")
        release_snapshot.set()
        issuance.result(timeout=5)

    with pytest.raises(ValueError, match="evidence changed after issuance"):
        packet.canonical_json()


def test_canonical_export_does_not_trust_mutable_module_digest_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A caller must not forge post-issuance integrity by replacing the module digest binding."""
    packet = _build_packet()
    creation_digest = packet.sha256_digest()
    object.__setattr__(packet, "reason_code", "administrative_correction")

    class _ForgedDigest:
        def hexdigest(self) -> str:
            return creation_digest

    monkeypatch.setattr(review_module, "sha256", lambda _payload: _ForgedDigest())

    with pytest.raises(ValueError, match="evidence changed after issuance"):
        packet.canonical_json()
