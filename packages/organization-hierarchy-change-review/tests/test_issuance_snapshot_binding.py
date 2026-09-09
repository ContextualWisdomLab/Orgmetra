"""Regressions for hierarchy-review issuance snapshot authority."""

from datetime import date, datetime, timezone
import json

import pytest

import orgmetra_organization_hierarchy_change_review.review as review_module
from orgmetra_organization_hierarchy_change_review import (
    build_organization_hierarchy_change_review_packet,
)


def _packet_kwargs(*, change_suffix: str, reviewer_suffix: str) -> dict[str, object]:
    """Return one bounded hierarchy-change review input set for this regression."""
    return {
        "tenant_record_id": "0195c23d-9f00-7000-8000-000000000001",
        "organization_hierarchy_change_reference": (
            f"organization_hierarchy_change:{change_suffix}"
        ),
        "organization_unit_reference": (
            "organization_unit:0195c23d-9f00-7000-8000-000000000002"
        ),
        "current_parent_organization_unit_reference": (
            "organization_unit:0195c23d-9f00-7000-8000-000000000003"
        ),
        "proposed_parent_organization_unit_reference": (
            "organization_unit:0195c23d-9f00-7000-8000-000000000004"
        ),
        "effective_on": date(2026, 9, 1),
        "organization_unit_snapshot_digest": "a" * 64,
        "hierarchy_snapshot_digest": "b" * 64,
        "requester_reference": "actor:22222222-2222-4222-8222-222222222222",
        "reviewer_reference": f"actor:{reviewer_suffix}",
        "purpose_code": "organization_hierarchy_change_review",
        "reason_code": "organizational_realignment",
        "recorded_at": datetime(2026, 8, 23, 7, 0, tzinfo=timezone.utc),
    }


def _valid_kwargs(*, change_suffix: str) -> dict[str, object]:
    """Return valid review evidence with an independent reviewer."""
    return _packet_kwargs(
        change_suffix=change_suffix,
        reviewer_suffix="33333333-3333-4333-8333-333333333333",
    )


def test_issuance_does_not_trust_mutable_module_snapshot_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate the packet being issued even if the module snapshot helper is replaced."""
    valid_packet = build_organization_hierarchy_change_review_packet(
        **_valid_kwargs(change_suffix="77777777-7777-4777-8777-777777777777")
    )
    trusted_snapshot = review_module._snapshot(valid_packet)
    monkeypatch.setattr(review_module, "_snapshot", lambda packet: trusted_snapshot)

    invalid = _packet_kwargs(
        change_suffix="88888888-8888-4888-8888-888888888888",
        reviewer_suffix="22222222-2222-4222-8222-222222222222",
    )
    with pytest.raises(ValueError, match="reviewer_reference must identify a different accountable actor"):
        build_organization_hierarchy_change_review_packet(**invalid)


def test_issuance_does_not_trust_mutable_module_payload_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bind canonical bytes to the validated issuance snapshot, not a later module helper."""
    expected_change_reference = (
        "organization_hierarchy_change:99999999-9999-4999-8999-999999999999"
    )
    monkeypatch.setattr(
        review_module,
        "_payload_from_snapshot",
        lambda snapshot: {
            "organization_hierarchy_change_reference": (
                "organization_hierarchy_change:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
            )
        },
    )

    packet = build_organization_hierarchy_change_review_packet(
        **_valid_kwargs(change_suffix="99999999-9999-4999-8999-999999999999")
    )

    assert json.loads(packet.canonical_json())["organization_hierarchy_change_reference"] == (
        expected_change_reference
    )


def test_issuance_does_not_trust_mutable_module_serializer_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep issued canonical JSON bound to the runtime serializer selected at import."""
    monkeypatch.setattr(review_module, "_canonical_payload_json", lambda payload: "{}")

    packet = build_organization_hierarchy_change_review_packet(
        **_valid_kwargs(change_suffix="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
    )

    assert json.loads(packet.canonical_json())["organization_hierarchy_change_reference"] == (
        "organization_hierarchy_change:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
    )
