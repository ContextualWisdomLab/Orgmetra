"""Regression coverage for string-subclass evidence-boundary integrity."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from orgmetra_interview_plan import build_structured_interview_plan


class ForgedReference(str):
    """String subclass that forges namespace/suffix validation while keeping hostile text."""

    def startswith(self, prefix, *args):  # type: ignore[no-untyped-def]
        """Pretend the hostile value carries every requested namespace."""
        return True

    def __getitem__(self, key):  # type: ignore[no-untyped-def]
        """Return a valid UUIDv4 only when validation slices the reference suffix."""
        if isinstance(key, slice):
            return "11111111-1111-4111-8111-111111111111"
        return super().__getitem__(key)


class ForgedTenantUUIDText(str):
    """String subclass that forges UUID parsing and canonical-equality checks."""

    def replace(self, old, new, *args):  # type: ignore[no-untyped-def]
        """Feed UUID() canonical text instead of the stored hostile tenant text."""
        canonical = "12345678-1234-4234-8234-123456789abc"
        return canonical.replace(old, new, *args)

    def __eq__(self, other):  # type: ignore[no-untyped-def]
        """Claim canonical equality while keeping the original hostile payload."""
        if other is None:
            return False
        return True

    def __ne__(self, other):  # type: ignore[no-untyped-def]
        """Keep UUID constructor sentinel checks working while defeating canonicality."""
        if other is None:
            return True
        return False


def valid_kwargs() -> dict[str, object]:
    """Return one otherwise valid structured-interview plan input."""
    return {
        "tenant_record_id": "12345678-1234-4234-8234-123456789abc",
        "interview_plan_reference": "interview_plan:11111111-1111-4111-8111-111111111111",
        "requisition_reference": "requisition:22222222-2222-4222-8222-222222222222",
        "job_profile_reference": "job_profile:33333333-3333-4333-8333-333333333333",
        "job_analysis_reference": "job_analysis:44444444-4444-4444-8444-444444444444",
        "job_analysis_digest": "a" * 64,
        "question_set_reference": "question_set:55555555-5555-4555-8555-555555555555",
        "question_set_digest": "b" * 64,
        "question_competency_map_reference": "question_competency_map:66666666-6666-4666-8666-666666666666",
        "question_competency_map_digest": "d" * 64,
        "rating_anchor_reference": "rating_anchor:77777777-7777-4777-8777-777777777777",
        "rating_anchor_digest": "c" * 64,
        "competency_references": (
            "competency:88888888-8888-4888-8888-888888888888",
            "competency:99999999-9999-4999-8999-999999999999",
        ),
        "panel_actor_references": (
            "actor:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            "actor:cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        ),
        "question_count": 4,
        "purpose_code": "structured_interview_plan",
        "reason_code": "approved_requisition_interview",
        "generated_at": datetime(2026, 8, 21, 5, 0, tzinfo=timezone.utc),
    }


def test_rejects_reference_string_subclass_that_can_forge_namespace_validation() -> None:
    """Canonical evidence must never retain text that only pretended to match a namespace."""
    kwargs = valid_kwargs()
    kwargs["interview_plan_reference"] = ForgedReference("attacker-controlled-reference-data")

    with pytest.raises(ValueError, match="interview_plan_reference"):
        build_structured_interview_plan(**kwargs)


def test_rejects_tenant_string_subclass_that_can_forge_uuid_validation() -> None:
    """Authoritative tenant identity must be exact built-in text before UUID parsing."""
    kwargs = valid_kwargs()
    kwargs["tenant_record_id"] = ForgedTenantUUIDText("not-a-tenant-uuid")

    with pytest.raises(ValueError, match="tenant_record_id"):
        build_structured_interview_plan(**kwargs)
