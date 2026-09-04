"""Regression coverage for string-subclass evidence-boundary integrity."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone

import pytest

from orgmetra_employment_separation_review import build_employment_separation_review_packet


class ForgedReference(str):
    def startswith(self, prefix, *args):  # type: ignore[no-untyped-def]
        return True

    def split(self, sep=None, maxsplit=-1):  # type: ignore[no-untyped-def]
        return ["evil", "22222222-2222-4222-8222-222222222222"]


class ForgedTenantUUIDText(str):
    def replace(self, old, new, *args):  # type: ignore[no-untyped-def]
        canonical = "11111111-1111-4111-8111-111111111111"
        return canonical.replace(old, new, *args)

    def __eq__(self, other):  # type: ignore[no-untyped-def]
        return other is not None

    def __ne__(self, other):  # type: ignore[no-untyped-def]
        return other is None


class ForgedGovernanceText(str):
    """Forge fixed equality and allow-list membership while retaining hostile text."""

    def __eq__(self, other):  # type: ignore[no-untyped-def]
        return True

    def __ne__(self, other):  # type: ignore[no-untyped-def]
        return False

    def __hash__(self) -> int:
        return hash("voluntary_resignation")


def valid_kwargs() -> dict[str, object]:
    return {
        "tenant_record_id": "11111111-1111-4111-8111-111111111111",
        "separation_review_reference": "employment_separation_review:22222222-2222-4222-8222-222222222222",
        "person_record_reference": "person_record:33333333-3333-4333-8333-333333333333",
        "employment_record_reference": "employment_record:44444444-4444-4444-8444-444444444444",
        "active_assignment_snapshot_reference": "active_assignment_snapshot:55555555-5555-4555-8555-555555555555",
        "active_assignment_snapshot_digest": "a" * 64,
        "separation_policy_reference": "employment_separation_policy:66666666-6666-4666-8666-666666666666",
        "separation_policy_digest": "b" * 64,
        "separation_process_reference": "employment_separation_process:77777777-7777-4777-8777-777777777777",
        "separation_process_digest": "c" * 64,
        "final_pay_handoff_reference": "final_pay_handoff:88888888-8888-4888-8888-888888888888",
        "final_pay_handoff_digest": "d" * 64,
        "benefits_handoff_reference": "benefits_handoff:99999999-9999-4999-8999-999999999999",
        "benefits_handoff_digest": "e" * 64,
        "access_deprovisioning_plan_reference": "access_deprovisioning_plan:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "access_deprovisioning_plan_digest": "f" * 64,
        "asset_return_plan_reference": "asset_return_plan:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        "asset_return_plan_digest": "1" * 64,
        "knowledge_transfer_plan_reference": "knowledge_transfer_plan:cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        "knowledge_transfer_plan_digest": "2" * 64,
        "communication_plan_reference": "separation_communication_plan:dddddddd-dddd-4ddd-8ddd-dddddddddddd",
        "communication_plan_digest": "3" * 64,
        "requester_reference": "actor:eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
        "reviewer_reference": "actor:ffffffff-ffff-4fff-8fff-fffffffffff0",
        "purpose_code": "employment_separation_review",
        "reason_code": "voluntary_resignation",
        "proposed_separation_on": date(2026, 9, 30),
        "generated_at": datetime(2026, 8, 19, 9, 10, 15, 123456, tzinfo=timezone.utc),
    }


def test_rejects_reference_string_subclass_that_can_forge_namespace_validation() -> None:
    kwargs = valid_kwargs()
    kwargs["separation_review_reference"] = ForgedReference("evil:payload")
    with pytest.raises(ValueError, match="separation_review_reference"):
        build_employment_separation_review_packet(**kwargs)


def test_rejects_tenant_string_subclass_that_can_forge_uuid_validation() -> None:
    kwargs = valid_kwargs()
    kwargs["tenant_record_id"] = ForgedTenantUUIDText("not-a-tenant-uuid")
    with pytest.raises(ValueError, match="tenant_record_id"):
        build_employment_separation_review_packet(**kwargs)


def test_rejects_forged_purpose_and_reason_codes() -> None:
    purpose_kwargs = valid_kwargs()
    purpose_kwargs["purpose_code"] = ForgedGovernanceText("attacker_controlled_purpose")
    with pytest.raises(ValueError, match="purpose_code"):
        build_employment_separation_review_packet(**purpose_kwargs)

    reason_kwargs = valid_kwargs()
    reason_kwargs["reason_code"] = ForgedGovernanceText("attacker_controlled_reason")
    with pytest.raises(ValueError, match="reason_code"):
        build_employment_separation_review_packet(**reason_kwargs)


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
    packet = build_employment_separation_review_packet(**valid_kwargs())
    with pytest.raises(ValueError, match=field_name):
        replace(packet, **{field_name: ForgedGovernanceText("attacker_controlled_text")})


class OpaqueDigestText(str):
    """Retain hostile raw text while pretending to equal any reviewed digest."""

    def __eq__(self, other):  # type: ignore[no-untyped-def]
        return True

    def __ne__(self, other):  # type: ignore[no-untyped-def]
        return False

    def __hash__(self) -> int:
        return hash("a" * 64)


def test_rejects_digest_string_subclass_before_pattern_match() -> None:
    """Digest text cannot carry caller-defined runtime behavior into evidence."""
    kwargs = valid_kwargs()
    kwargs["separation_policy_digest"] = OpaqueDigestText("0" * 64)
    with pytest.raises(ValueError, match="separation_policy_digest"):
        build_employment_separation_review_packet(**kwargs)
