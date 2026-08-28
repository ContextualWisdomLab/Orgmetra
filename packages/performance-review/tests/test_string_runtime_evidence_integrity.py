"""Regression coverage for string-subclass evidence-boundary integrity."""

from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

from orgmetra_performance_review import build_performance_review_packet


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
        return hash("scheduled_cycle_review")


class ForgedDigest(str):
    """Valid-looking digest subclass that must not cross the evidence boundary."""


def valid_kwargs() -> dict[str, object]:
    """Return one otherwise valid performance-review packet input."""
    return {
        "tenant_record_id": "11111111-1111-4111-8111-111111111111",
        "performance_review_reference": "performance_review:22222222-2222-4222-8222-222222222222",
        "person_record_reference": "person_record:33333333-3333-4333-8333-333333333333",
        "employment_record_reference": "employment_record:44444444-4444-4444-8444-444444444444",
        "job_profile_reference": "job_profile:55555555-5555-4555-8555-555555555555",
        "performance_cycle_reference": "performance_cycle:66666666-6666-4666-8666-666666666666",
        "criterion_set_reference": "criterion_set:77777777-7777-4777-8777-777777777777",
        "criterion_set_digest": "a" * 64,
        "goal_plan_reference": "performance_goal_plan:88888888-8888-4888-8888-888888888888",
        "goal_plan_digest": "b" * 64,
        "criterion_observation_snapshot_reference": "criterion_observation_snapshot:99999999-9999-4999-8999-999999999999",
        "criterion_observation_snapshot_digest": "c" * 64,
        "development_plan_reference": "development_plan:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "development_plan_digest": "d" * 64,
        "reviewer_reference": "actor:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        "purpose_code": "performance_review",
        "reason_code": "scheduled_cycle_review",
        "review_period_start": date(2026, 1, 1),
        "review_period_end": date(2026, 6, 30),
    }


def test_rejects_reference_string_subclass_that_can_forge_namespace_validation() -> None:
    kwargs = valid_kwargs()
    kwargs["performance_review_reference"] = ForgedReference("evil:payload")
    with pytest.raises(ValueError, match="performance_review_reference"):
        build_performance_review_packet(**kwargs)


def test_rejects_tenant_string_subclass_that_can_forge_uuid_validation() -> None:
    kwargs = valid_kwargs()
    kwargs["tenant_record_id"] = ForgedTenantUUIDText("not-a-tenant-uuid")
    with pytest.raises(ValueError, match="tenant_record_id"):
        build_performance_review_packet(**kwargs)


def test_rejects_reason_code_string_subclass_that_can_forge_allow_list_membership() -> None:
    kwargs = valid_kwargs()
    kwargs["reason_code"] = ForgedGovernanceText("attacker_controlled_reason")
    with pytest.raises(ValueError, match="reason_code"):
        build_performance_review_packet(**kwargs)


def test_rejects_purpose_code_string_subclass_that_can_forge_fixed_code_check() -> None:
    kwargs = valid_kwargs()
    kwargs["purpose_code"] = ForgedGovernanceText("attacker_controlled_purpose")
    with pytest.raises(ValueError, match="purpose_code"):
        build_performance_review_packet(**kwargs)


@pytest.mark.parametrize(
    "field_name",
    (
        "criterion_set_digest",
        "goal_plan_digest",
        "criterion_observation_snapshot_digest",
        "development_plan_digest",
    ),
)
def test_rejects_digest_string_subclass_at_all_digest_boundaries(field_name: str) -> None:
    """Every trust-bearing SHA-256 field requires exact built-in text."""
    kwargs = valid_kwargs()
    kwargs[field_name] = ForgedDigest(str(kwargs[field_name]))
    with pytest.raises(ValueError, match=field_name):
        build_performance_review_packet(**kwargs)


@pytest.mark.parametrize(
    ("field_name", "message"),
    (
        ("decision_authority", "decision_authority"),
        ("review_state", "review_state"),
        ("scope_verification_state", "scope_verification_state"),
        ("next_action", "next_action"),
    ),
)
def test_rejects_forged_direct_construction_constant_text(field_name: str, message: str) -> None:
    packet = build_performance_review_packet(**valid_kwargs())
    with pytest.raises(ValueError, match=message):
        replace(packet, **{field_name: ForgedGovernanceText("attacker_controlled_text")})
