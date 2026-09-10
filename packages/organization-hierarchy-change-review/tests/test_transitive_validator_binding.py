"""Regressions for transitive hierarchy-review validation authority."""

from datetime import date, datetime, timedelta, timezone
from typing import Any

import pytest

import orgmetra_organization_hierarchy_change_review.review as review_module
from orgmetra_organization_hierarchy_change_review import (
    OrganizationHierarchyChangeReviewPacket,
    build_organization_hierarchy_change_review_packet,
)


def _values(change_suffix: str) -> dict[str, Any]:
    """Return isolated valid evidence for one transitive-binding regression."""
    return {
        "tenant_record_id": "0195c23d-9f00-7000-8000-000000000001",
        "organization_hierarchy_change_reference": (
            f"organization_hierarchy_change:{change_suffix}"
        ),
        "organization_unit_reference": "organization_unit:0195c23d-9f00-7000-8000-000000000002",
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
        "reviewer_reference": "actor:33333333-3333-4333-8333-333333333333",
        "purpose_code": "organization_hierarchy_change_review",
        "reason_code": "organizational_realignment",
        "recorded_at": datetime(2026, 8, 23, 7, 0, tzinfo=timezone.utc),
    }


def _build(change_suffix: str, **overrides: object) -> OrganizationHierarchyChangeReviewPacket:
    """Build isolated evidence while allowing one test-specific invalid value."""
    values = _values(change_suffix)
    values.update(overrides)
    return build_organization_hierarchy_change_review_packet(**values)


def test_issuance_does_not_trust_mutable_transitive_reference_validator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject invalid references even if a transitive module helper is replaced."""
    monkeypatch.setattr(review_module, "_validate_reference", lambda *args, **kwargs: None)

    with pytest.raises(ValueError, match="organization_unit_reference must be a canonical"):
        _build(
            "66666666-6666-4666-8666-666666666666",
            organization_unit_reference="organization_unit:not-a-uuid",
        )


def test_issuance_does_not_trust_mutable_digest_pattern_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep digest grammar bound even if the later module pattern is permissive."""

    class PermissivePattern:
        """Model a caller-owned replacement that accepts every digest."""

        @staticmethod
        def fullmatch(value: object) -> object:
            """Return a truthy match sentinel for every supplied value."""
            return value

    monkeypatch.setattr(review_module, "_DIGEST_PATTERN", PermissivePattern())

    with pytest.raises(ValueError, match="hierarchy_snapshot_digest must be lowercase SHA-256 hex"):
        _build(
            "77777777-7777-4777-8777-777777777777",
            hierarchy_snapshot_digest="not-a-digest",
        )


def test_issuance_does_not_trust_mutable_purpose_constant_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep governed purpose semantics bound to the constructed validator authority."""
    monkeypatch.setattr(review_module, "_PURPOSE_CODE", "caller_selected_purpose")

    with pytest.raises(ValueError, match="purpose_code must remain"):
        _build(
            "88888888-8888-4888-8888-888888888888",
            purpose_code="caller_selected_purpose",
        )


def test_issuance_does_not_trust_mutable_timestamp_validator_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep future-time rejection even if the later module helper becomes a no-op."""
    monkeypatch.setattr(review_module, "_validate_issuance_timestamp", lambda value: None)

    with pytest.raises(ValueError, match="recorded_at must not be in the future"):
        _build(
            "99999999-9999-4999-8999-999999999999",
            recorded_at=datetime.now(timezone.utc) + timedelta(days=1),
        )


def test_canonicalization_does_not_trust_mutable_json_module_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep canonical serialization bound to the serializer selected at definition time."""
    monkeypatch.setattr(review_module, "json", object())

    packet = _build("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    assert packet.canonical_json().startswith('{"contains_employment_decision":false')
