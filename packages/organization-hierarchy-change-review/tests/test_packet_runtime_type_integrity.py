"""Regression for packet-level checked-versus-emitted runtime substitution."""

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest

from orgmetra_organization_hierarchy_change_review import (
    OrganizationHierarchyChangeReviewPacket,
    build_organization_hierarchy_change_review_packet,
)


def test_rejects_packet_runtime_subclass_before_trust_field_validation() -> None:
    """Do not let packet polymorphism reach validation or canonical emission."""
    with pytest.raises(TypeError, match="does not support caller-defined subclasses"):

        class TenantSwapPacket(OrganizationHierarchyChangeReviewPacket):
            """Try to change one trust-bearing field across repeated reads."""

            def __getattribute__(self, name: str) -> object:
                """Swap tenant evidence without mutating the inherited frozen slots."""
                if name == "tenant_record_id":
                    return "not-a-uuid"
                return super().__getattribute__(name)


def test_rejects_subclass_that_bypasses_base_post_init() -> None:
    """A subclass must not suppress the base validation hook entirely."""
    with pytest.raises(TypeError, match="does not support caller-defined subclasses"):

        class PostInitBypassPacket(OrganizationHierarchyChangeReviewPacket):
            """Try to replace the inherited post-init validator with a no-op."""

            def __post_init__(self) -> None:
                """Suppress all base validation if subclass creation were permitted."""


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
