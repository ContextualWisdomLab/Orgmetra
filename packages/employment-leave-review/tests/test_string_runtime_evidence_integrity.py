"""Regression coverage for string-subclass evidence-boundary integrity."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

import pytest

from orgmetra_employment_leave_review import build_employment_leave_review_packet


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
        return other is not None

    def __ne__(self, other):  # type: ignore[no-untyped-def]
        return other is None


class ForgedGovernanceText(str):
    """String subclass that forges fixed equality and allow-list membership."""

    def __eq__(self, other):  # type: ignore[no-untyped-def]
        return True

    def __ne__(self, other):  # type: ignore[no-untyped-def]
        return False

    def __hash__(self) -> int:
        return hash("policy_entitlement_review")


def valid_kwargs() -> dict[str, object]:
    """Return one otherwise valid employment-leave review packet input."""
    digest = "a" * 64
    return {
        "tenant_record_id": "11111111-1111-4111-8111-111111111111",
        "leave_review_reference": "employment_leave_review:22222222-2222-4222-8222-222222222222",
        "person_record_reference": "person_record:33333333-3333-4333-8333-333333333333",
        "employment_record_reference": "employment_record:44444444-4444-4444-8444-444444444444",
        "active_assignment_snapshot_reference": "active_assignment_snapshot:55555555-5555-4555-8555-555555555555",
        "active_assignment_snapshot_digest": digest,
        "leave_case_reference": "leave_case:66666666-6666-4666-8666-666666666666",
        "leave_case_digest": digest,
        "leave_policy_reference": "leave_policy:77777777-7777-4777-8777-777777777777",
        "leave_policy_digest": digest,
        "work_continuity_plan_reference": "work_continuity_plan:88888888-8888-4888-8888-888888888888",
        "work_continuity_plan_digest": digest,
        "benefits_continuity_plan_reference": "benefits_continuity_plan:99999999-9999-4999-8999-999999999999",
        "benefits_continuity_plan_digest": digest,
        "return_to_work_plan_reference": "return_to_work_plan:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "return_to_work_plan_digest": digest,
        "handling_policy_reference": "personal_data_handling_policy:dddddddd-dddd-4ddd-8ddd-dddddddddddd",
        "handling_policy_digest": digest,
        "retention_policy_reference": "retention_policy:eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
        "retention_policy_digest": digest,
        "requester_reference": "actor:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        "reviewer_reference": "actor:cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        "purpose_code": "employment_leave_review",
        "reason_code": "policy_entitlement_review",
        "requested_leave_start_on": date(2026, 9, 1),
        "requested_leave_end_on": date(2026, 9, 30),
        "generated_at": datetime(2026, 8, 19, 11, 24, 51, 123456, tzinfo=timezone(timedelta(hours=9))),
    }


def test_rejects_reference_string_subclass_that_can_forge_namespace_validation() -> None:
    kwargs = valid_kwargs()
    kwargs["leave_review_reference"] = ForgedReference("evil:payload")
    with pytest.raises(ValueError, match="leave_review_reference"):
        build_employment_leave_review_packet(**kwargs)


def test_rejects_tenant_string_subclass_that_can_forge_uuid_validation() -> None:
    kwargs = valid_kwargs()
    kwargs["tenant_record_id"] = ForgedTenantUUIDText("not-a-tenant-uuid")
    with pytest.raises(ValueError, match="tenant_record_id"):
        build_employment_leave_review_packet(**kwargs)


def test_rejects_forged_purpose_and_reason_codes() -> None:
    purpose_kwargs = valid_kwargs()
    purpose_kwargs["purpose_code"] = ForgedGovernanceText("attacker_controlled_purpose")
    with pytest.raises(ValueError, match="purpose_code"):
        build_employment_leave_review_packet(**purpose_kwargs)

    reason_kwargs = valid_kwargs()
    reason_kwargs["reason_code"] = ForgedGovernanceText("attacker_controlled_reason")
    with pytest.raises(ValueError, match="reason_code"):
        build_employment_leave_review_packet(**reason_kwargs)


@pytest.mark.parametrize(
    "field_name",
    (
        "decision_authority",
        "review_state",
        "scope_verification_state",
        "mutation_state",
        "external_execution_state",
        "next_action",
    ),
)
def test_rejects_forged_direct_construction_constant_text(field_name: str) -> None:
    packet = build_employment_leave_review_packet(**valid_kwargs())
    with pytest.raises(ValueError, match=field_name):
        replace(packet, **{field_name: ForgedGovernanceText("attacker_controlled_text")})


def test_rejects_digest_string_subclass_before_pattern_match() -> None:
    """Digest text cannot carry caller-defined runtime behavior into evidence."""
    kwargs = valid_kwargs()
    kwargs["handling_policy_digest"] = ForgedGovernanceText("b" * 64)
    with pytest.raises(ValueError, match="handling_policy_digest"):
        build_employment_leave_review_packet(**kwargs)
