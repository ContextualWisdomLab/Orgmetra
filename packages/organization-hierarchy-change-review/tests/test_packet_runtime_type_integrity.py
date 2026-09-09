"""Regression for packet-level checked-versus-emitted runtime substitution."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import fields
from datetime import date, datetime, timezone
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
    with pytest.raises(ValueError, match="runtime types changed after issuance"):
        packet.canonical_json()


def test_canonical_export_validates_and_emits_one_snapshot_during_concurrent_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A mutation after snapshot capture must not change the payload validated for this export."""
    packet = _build_packet()
    expected_json = packet.canonical_json()
    canonical_date_entered = Event()
    release_canonical_date = Event()
    original_canonical_date = review_module._canonical_date

    def blocking_canonical_date(value: object) -> str:
        canonical_date_entered.set()
        if not release_canonical_date.wait(timeout=5):
            raise AssertionError("test did not release canonical date rendering")
        return original_canonical_date(value)

    monkeypatch.setattr(review_module, "_canonical_date", blocking_canonical_date)
    with ThreadPoolExecutor(max_workers=1) as executor:
        export = executor.submit(packet.canonical_json)
        assert canonical_date_entered.wait(timeout=5)
        object.__setattr__(packet, "reason_code", "administrative_correction")
        release_canonical_date.set()
        assert export.result(timeout=5) == expected_json

    with pytest.raises(ValueError, match="evidence changed after issuance"):
        packet.canonical_json()


def test_issuance_validates_and_seals_one_snapshot_during_concurrent_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not seal a semantic value that changed after its validation already ran."""
    template = _build_packet()
    packet = object.__new__(OrganizationHierarchyChangeReviewPacket)
    for field in fields(OrganizationHierarchyChangeReviewPacket):
        object.__setattr__(packet, field.name, object.__getattribute__(template, field.name))
    object.__setattr__(
        packet,
        "organization_hierarchy_change_reference",
        f"organization_hierarchy_change:{uuid4()}",
    )

    issuance_timestamp_entered = Event()
    release_issuance_timestamp = Event()
    original_validate_issuance_timestamp = review_module._validate_issuance_timestamp

    def blocking_validate_issuance_timestamp(value: object) -> None:
        original_validate_issuance_timestamp(value)
        issuance_timestamp_entered.set()
        if not release_issuance_timestamp.wait(timeout=5):
            raise AssertionError("test did not release issuance timestamp validation")

    monkeypatch.setattr(
        review_module,
        "_validate_issuance_timestamp",
        blocking_validate_issuance_timestamp,
    )
    with ThreadPoolExecutor(max_workers=1) as executor:
        issuance = executor.submit(packet.__post_init__)
        assert issuance_timestamp_entered.wait(timeout=5)
        object.__setattr__(packet, "reason_code", "unreviewed_override")
        release_issuance_timestamp.set()
        with pytest.raises(
            ValueError,
            match="reason_code must use the reviewed hierarchy-change vocabulary",
        ):
            issuance.result(timeout=5)
