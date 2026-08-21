"""Regression coverage for string-subclass evidence-boundary integrity."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone

import pytest

from orgmetra_assignment_change_review import build_assignment_change_review_packet


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
    """String subclass that forges equality and closed-vocabulary membership."""

    def __eq__(self, other):  # type: ignore[no-untyped-def]
        return True

    def __ne__(self, other):  # type: ignore[no-untyped-def]
        return False

    def __hash__(self) -> int:
        return hash("workforce_reallocation")


def valid_kwargs() -> dict[str, object]:
    """Return one otherwise valid assignment-change review packet input."""
    return {
        "tenant_record_id": "11111111-1111-4111-8111-111111111111",
        "assignment_change_review_reference": "assignment_change_review:22222222-2222-4222-8222-222222222222",
        "person_record_reference": "person_record:33333333-3333-4333-8333-333333333333",
        "employment_record_reference": "employment_record:44444444-4444-4444-8444-444444444444",
        "current_assignment_reference": "assignment_record:55555555-5555-4555-8555-555555555555",
        "current_job_profile_reference": "job_profile:66666666-6666-4666-8666-666666666666",
        "current_position_record_reference": "position_record:77777777-7777-4777-8777-777777777777",
        "proposed_job_profile_reference": "job_profile:88888888-8888-4888-8888-888888888888",
        "proposed_position_record_reference": "position_record:99999999-9999-4999-8999-999999999999",
        "current_scope_snapshot_reference": "assignment_scope_snapshot:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "current_scope_snapshot_digest": "a" * 64,
        "allocation_plan_reference": "workforce_allocation_plan:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        "allocation_plan_digest": "b" * 64,
        "allocation_policy_reference": "workforce_allocation_policy:abababab-abab-4bab-8bab-abababababab",
        "allocation_policy_digest": "c" * 64,
        "worker_impact_assessment_reference": "worker_impact_assessment:cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        "worker_impact_assessment_digest": "d" * 64,
        "communication_plan_reference": "assignment_communication_plan:dddddddd-dddd-4ddd-8ddd-dddddddddddd",
        "communication_plan_digest": "e" * 64,
        "requester_reference": "actor:eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
        "reviewer_reference": "actor:ffffffff-ffff-4fff-8fff-fffffffffff0",
        "purpose_code": "assignment_change_review",
        "reason_code": "workforce_reallocation",
        "requested_effective_on": date(2026, 9, 1),
        "generated_at": datetime(2026, 8, 19, 6, 30, 15, 123456, tzinfo=timezone.utc),
    }


def test_rejects_reference_string_subclass_that_can_forge_namespace_validation() -> None:
    kwargs = valid_kwargs()
    kwargs["assignment_change_review_reference"] = ForgedReference("evil:payload")
    with pytest.raises(ValueError, match="assignment_change_review_reference"):
        build_assignment_change_review_packet(**kwargs)


def test_rejects_tenant_string_subclass_that_can_forge_uuid_validation() -> None:
    kwargs = valid_kwargs()
    kwargs["tenant_record_id"] = ForgedTenantUUIDText("not-a-tenant-uuid")
    with pytest.raises(ValueError, match="tenant_record_id"):
        build_assignment_change_review_packet(**kwargs)


def test_rejects_forged_purpose_and_reason_codes() -> None:
    purpose_kwargs = valid_kwargs()
    purpose_kwargs["purpose_code"] = ForgedGovernanceText("attacker_controlled_purpose")
    with pytest.raises(ValueError, match="purpose_code"):
        build_assignment_change_review_packet(**purpose_kwargs)

    reason_kwargs = valid_kwargs()
    reason_kwargs["reason_code"] = ForgedGovernanceText("attacker_controlled_reason")
    with pytest.raises(ValueError, match="reason_code"):
        build_assignment_change_review_packet(**reason_kwargs)


@pytest.mark.parametrize(
    "field_name",
    ("decision_authority", "review_state", "scope_verification_state", "mutation_state", "next_action"),
)
def test_rejects_forged_direct_construction_constant_text(field_name: str) -> None:
    packet = build_assignment_change_review_packet(**valid_kwargs())
    with pytest.raises(ValueError, match=field_name):
        replace(packet, **{field_name: ForgedGovernanceText("attacker_controlled_text")})
