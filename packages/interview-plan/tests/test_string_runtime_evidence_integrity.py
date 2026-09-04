"""Regression coverage for string-subclass evidence-boundary integrity."""

from __future__ import annotations

from dataclasses import replace
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
        """Pretend hostile tenant text equals every non-null comparison target."""
        if other is None:
            return False
        return True

    def __ne__(self, other):  # type: ignore[no-untyped-def]
        """Pretend hostile tenant text differs only from a null comparison target."""
        if other is None:
            return True
        return False


class ForgedGovernanceCode(str):
    """String subclass that forges fixed-code equality and allow-list membership."""

    def __eq__(self, other):  # type: ignore[no-untyped-def]
        """Pretend hostile governance text equals every comparison target."""
        return True

    def __ne__(self, other):  # type: ignore[no-untyped-def]
        """Pretend hostile governance text never differs from a comparison target."""
        return False

    def __hash__(self) -> int:
        """Return the hash of an allowed reason code to probe set membership defenses."""
        return hash("approved_requisition_interview")


class SwitchingReferenceTuple(tuple):
    """Tuple subclass that changes references after validation has already completed."""

    def __new__(
        cls,
        values: tuple[str, ...],
        forged_values: tuple[str, ...],
    ) -> "SwitchingReferenceTuple":
        """Store valid tuple payload plus later forged references for canonicalization."""
        instance = super().__new__(cls, values)
        instance._forged_values = forged_values
        instance._iteration_count = 0
        return instance

    def __iter__(self):  # type: ignore[no-untyped-def]
        """Yield valid references twice, then substitute forged references on later reads."""
        self._iteration_count += 1
        if self._iteration_count >= 3:
            return iter(self._forged_values)
        return tuple.__iter__(self)


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
    """Reject reference subclasses before forged namespace behavior can affect evidence."""
    kwargs = valid_kwargs()
    kwargs["interview_plan_reference"] = ForgedReference("attacker-controlled-reference-data")
    with pytest.raises(ValueError, match="interview_plan_reference"):
        build_structured_interview_plan(**kwargs)


def test_rejects_tenant_string_subclass_that_can_forge_uuid_validation() -> None:
    """Reject tenant-text subclasses before forged UUID behavior can affect identity evidence."""
    kwargs = valid_kwargs()
    kwargs["tenant_record_id"] = ForgedTenantUUIDText("not-a-tenant-uuid")
    with pytest.raises(ValueError, match="tenant_record_id"):
        build_structured_interview_plan(**kwargs)


def test_rejects_purpose_code_string_subclass_that_can_forge_fixed_code_check() -> None:
    """Reject purpose-code subclasses before forged equality can bypass the closed code."""
    kwargs = valid_kwargs()
    kwargs["purpose_code"] = ForgedGovernanceCode("attacker_controlled_purpose")
    with pytest.raises(ValueError, match="purpose_code"):
        build_structured_interview_plan(**kwargs)


def test_rejects_reason_code_string_subclass_that_can_forge_allow_list_check() -> None:
    """Reject reason-code subclasses before forged equality or hashing can bypass policy."""
    kwargs = valid_kwargs()
    kwargs["reason_code"] = ForgedGovernanceCode("attacker_controlled_reason")
    with pytest.raises(ValueError, match="reason_code"):
        build_structured_interview_plan(**kwargs)


@pytest.mark.parametrize(
    ("field", "forged_value"),
    [
        ("review_state", ForgedGovernanceCode("attacker_controlled_review_state")),
        ("next_action", ForgedGovernanceCode("attacker_controlled_next_action")),
    ],
)
def test_rejects_fixed_governance_text_subclasses_after_plan_construction(
    field: str,
    forged_value: ForgedGovernanceCode,
) -> None:
    """Reject replacement-time string subclasses before immutable governance text can be forged."""
    candidate_plan = build_structured_interview_plan(**valid_kwargs())
    with pytest.raises(ValueError, match=field):
        replace(candidate_plan, **{field: forged_value})


@pytest.mark.parametrize(
    ("field", "forged_values"),
    [
        (
            "competency_references",
            (
                "competency:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                "competency:dddddddd-dddd-4ddd-8ddd-dddddddddddd",
            ),
        ),
        (
            "panel_actor_references",
            (
                "actor:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                "actor:dddddddd-dddd-4ddd-8ddd-dddddddddddd",
            ),
        ),
    ],
)
def test_rejects_reference_tuple_subclasses_before_iteration_can_switch_evidence(
    field: str,
    forged_values: tuple[str, ...],
) -> None:
    """Reject tuple subclasses that can change canonical references after validation."""
    kwargs = valid_kwargs()
    original_values = kwargs[field]
    assert type(original_values) is tuple
    kwargs[field] = SwitchingReferenceTuple(original_values, forged_values)
    with pytest.raises(ValueError, match=field):
        build_structured_interview_plan(**kwargs)
