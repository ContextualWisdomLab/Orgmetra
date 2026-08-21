"""Regression coverage for string-subclass evidence-boundary integrity."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from orgmetra_compensation_change_review import build_compensation_change_review_packet


class ForgedReference(str):
    """String subclass that forges namespace and UUID suffix validation."""

    def startswith(self, prefix, *args):  # type: ignore[no-untyped-def]
        return True

    def split(self, sep=None, maxsplit=-1):  # type: ignore[no-untyped-def]
        return ["evil", "22222222-2222-4222-8222-222222222222"]


class ForgedTenantUUIDText(str):
    """String subclass that forges UUID parsing and canonical-equality checks."""

    def replace(self, old, new, *args):  # type: ignore[no-untyped-def]
        canonical = "11111111-1111-4111-8111-111111111111"
        return canonical.replace(old, new, *args)

    def __eq__(self, other):  # type: ignore[no-untyped-def]
        if other is None:
            return False
        return True

    def __ne__(self, other):  # type: ignore[no-untyped-def]
        if other is None:
            return True
        return False


def valid_kwargs() -> dict[str, object]:
    """Return one otherwise valid compensation-change review packet input."""
    return {
        "tenant_record_id": "11111111-1111-4111-8111-111111111111",
        "compensation_review_reference": "compensation_change_review:22222222-2222-4222-8222-222222222222",
        "person_record_reference": "person_record:33333333-3333-4333-8333-333333333333",
        "employment_record_reference": "employment_record:44444444-4444-4444-8444-444444444444",
        "active_assignment_snapshot_reference": "active_assignment_snapshot:55555555-5555-4555-8555-555555555555",
        "active_assignment_snapshot_digest": "a" * 64,
        "current_compensation_snapshot_reference": "compensation_snapshot:66666666-6666-4666-8666-666666666666",
        "current_compensation_snapshot_digest": "b" * 64,
        "proposed_compensation_plan_reference": "compensation_plan:77777777-7777-4777-8777-777777777777",
        "proposed_compensation_plan_digest": "c" * 64,
        "compensation_policy_reference": "compensation_policy:88888888-8888-4888-8888-888888888888",
        "compensation_policy_digest": "d" * 64,
        "pay_equity_review_reference": "pay_equity_review:99999999-9999-4999-8999-999999999999",
        "pay_equity_review_digest": "e" * 64,
        "budget_authorization_reference": "budget_authorization:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "budget_authorization_digest": "f" * 64,
        "payroll_handoff_plan_reference": "payroll_handoff_plan:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        "payroll_handoff_plan_digest": "1" * 64,
        "requester_reference": "actor:cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        "reviewer_reference": "actor:dddddddd-dddd-4ddd-8ddd-dddddddddddd",
        "purpose_code": "compensation_change_review",
        "reason_code": "annual_compensation_review",
        "proposed_effective_on": date(2026, 10, 1),
        "generated_at": datetime(2026, 8, 19, 6, 12, 13, 456789, tzinfo=timezone.utc),
        "evidence_version": 1,
    }


def test_rejects_reference_string_subclass_that_can_forge_namespace_validation() -> None:
    kwargs = valid_kwargs()
    kwargs["compensation_review_reference"] = ForgedReference("evil:payload")
    with pytest.raises(ValueError, match="compensation_review_reference"):
        build_compensation_change_review_packet(**kwargs)


def test_rejects_tenant_string_subclass_that_can_forge_uuid_validation() -> None:
    kwargs = valid_kwargs()
    kwargs["tenant_record_id"] = ForgedTenantUUIDText("not-a-tenant-uuid")
    with pytest.raises(ValueError, match="tenant_record_id"):
        build_compensation_change_review_packet(**kwargs)
