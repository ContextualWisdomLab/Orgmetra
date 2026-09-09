"""Regression for post-issuance export-verifier capability binding."""

from datetime import date, datetime, timezone
import json
from uuid import uuid4

import pytest

import orgmetra_organization_hierarchy_change_review.review as review_module
from orgmetra_organization_hierarchy_change_review import (
    build_organization_hierarchy_change_review_packet,
)


def test_canonical_export_does_not_trust_mutable_module_payload_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A replaced module helper must not hide semantic mutation after issuance."""
    packet = build_organization_hierarchy_change_review_packet(
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
    issued_json = packet.canonical_json()
    issued_payload = json.loads(issued_json)
    object.__setattr__(packet, "reason_code", "administrative_correction")
    monkeypatch.setattr(review_module, "_payload", lambda _packet: issued_payload)

    with pytest.raises(ValueError, match="evidence changed after issuance"):
        packet.canonical_json()
