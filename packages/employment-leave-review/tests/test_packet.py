from dataclasses import replace
from datetime import date, datetime, timedelta, timezone, tzinfo
from hashlib import sha256
import json
from uuid import NAMESPACE_URL, uuid3, uuid5

import pytest

from orgmetra_employment_leave_review import (
    EmploymentLeaveReviewPacket,
    build_employment_leave_review_packet,
)

U = {
    "tenant": "11111111-1111-4111-8111-111111111111",
    "review": "22222222-2222-4222-8222-222222222222",
    "person": "33333333-3333-4333-8333-333333333333",
    "employment": "44444444-4444-4444-8444-444444444444",
    "snapshot": "55555555-5555-4555-8555-555555555555",
    "case": "66666666-6666-4666-8666-666666666666",
    "policy": "77777777-7777-4777-8777-777777777777",
    "work": "88888888-8888-4888-8888-888888888888",
    "benefits": "99999999-9999-4999-8999-999999999999",
    "return": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    "requester": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
    "reviewer": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
    "handling": "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
    "retention": "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
}
D = "a" * 64
UUID1_ID = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
NON_V4_IDS = {
    "uuid1_time_based": UUID1_ID,
    "uuid3_md5_deterministic": str(uuid3(NAMESPACE_URL, "https://orgmetra.invalid/leave")),
    "uuid5_sha1_deterministic": str(uuid5(NAMESPACE_URL, "https://orgmetra.invalid/leave")),
    "uuid7_time_ordered": "017f22e2-79b0-7cc3-98c4-dc0c0c07398f",
}


def args() -> dict[str, object]:
    """Return one realistic value-minimized leave-review fixture."""
    return {
        "tenant_record_id": U["tenant"],
        "leave_review_reference": f"employment_leave_review:{U['review']}",
        "person_record_reference": f"person_record:{U['person']}",
        "employment_record_reference": f"employment_record:{U['employment']}",
        "active_assignment_snapshot_reference": f"active_assignment_snapshot:{U['snapshot']}",
        "active_assignment_snapshot_digest": D,
        "leave_case_reference": f"leave_case:{U['case']}",
        "leave_case_digest": D,
        "leave_policy_reference": f"leave_policy:{U['policy']}",
        "leave_policy_digest": D,
        "work_continuity_plan_reference": f"work_continuity_plan:{U['work']}",
        "work_continuity_plan_digest": D,
        "benefits_continuity_plan_reference": f"benefits_continuity_plan:{U['benefits']}",
        "benefits_continuity_plan_digest": D,
        "return_to_work_plan_reference": f"return_to_work_plan:{U['return']}",
        "return_to_work_plan_digest": D,
        "handling_policy_reference": f"personal_data_handling_policy:{U['handling']}",
        "handling_policy_digest": D,
        "retention_policy_reference": f"retention_policy:{U['retention']}",
        "retention_policy_digest": D,
        "requester_reference": f"actor:{U['requester']}",
        "reviewer_reference": f"actor:{U['reviewer']}",
        "purpose_code": "employment_leave_review",
        "reason_code": "policy_entitlement_review",
        "requested_leave_start_on": date(2026, 9, 1),
        "requested_leave_end_on": date(2026, 9, 30),
        "generated_at": datetime(
            2026, 8, 19, 11, 24, 51, 123456, tzinfo=timezone(timedelta(hours=9))
        ),
    }


def packet() -> EmploymentLeaveReviewPacket:
    """Build the canonical fixture through the public builder."""
    return build_employment_leave_review_packet(**args())


def test_valid_packet_is_value_minimized_human_review_only_and_deterministic() -> None:
    p = packet()
    payload = json.loads(p.canonical_json())
    assert p.sha256_digest() == sha256(p.canonical_json().encode("utf-8")).hexdigest()
    assert payload["generated_at"] == "2026-08-19T02:24:51.123456Z"
    assert payload["contains_person_pii"] is True
    assert payload["contains_medical_or_family_values"] is False
    assert payload["decision_authority"] == "human_review_only"
    assert payload["handling_policy_reference"].startswith("personal_data_handling_policy:")
    assert payload["retention_policy_reference"].startswith("retention_policy:")
    assert "handling/retention policy" in p.next_action
    assert "medical/family evidence" in p.next_action
    assert "resolved actor identities are distinct" in p.next_action
    assert "person_record_reference" in payload
    assert "salary" not in payload


@pytest.mark.parametrize(
    ("field", "prefix"),
    [
        ("leave_review_reference", "employment_leave_review"),
        ("person_record_reference", "person_record"),
        ("employment_record_reference", "employment_record"),
        ("active_assignment_snapshot_reference", "active_assignment_snapshot"),
        ("leave_case_reference", "leave_case"),
        ("leave_policy_reference", "leave_policy"),
        ("work_continuity_plan_reference", "work_continuity_plan"),
        ("benefits_continuity_plan_reference", "benefits_continuity_plan"),
        ("return_to_work_plan_reference", "return_to_work_plan"),
        ("handling_policy_reference", "personal_data_handling_policy"),
        ("retention_policy_reference", "retention_policy"),
        ("requester_reference", "actor"),
        ("reviewer_reference", "actor"),
    ],
)
def test_reference_guards_reject_wrong_namespace_and_non_uuid(field: str, prefix: str) -> None:
    p = packet()
    with pytest.raises(ValueError):
        replace(p, **{field: "wrong:33333333-3333-4333-8333-333333333333"})
    with pytest.raises(ValueError):
        replace(p, **{field: f"{prefix}:Jane-Doe"})
    with pytest.raises(ValueError):
        replace(p, **{field: f"{prefix}:00000000-0000-0000-0000-000000000000"})
    with pytest.raises(ValueError):
        replace(p, **{field: 3})


@pytest.mark.parametrize("non_v4_id", sorted(NON_V4_IDS))
@pytest.mark.parametrize(
    ("field", "prefix"),
    [
        ("leave_review_reference", "employment_leave_review"),
        ("person_record_reference", "person_record"),
        ("employment_record_reference", "employment_record"),
        ("active_assignment_snapshot_reference", "active_assignment_snapshot"),
        ("leave_case_reference", "leave_case"),
        ("leave_policy_reference", "leave_policy"),
        ("work_continuity_plan_reference", "work_continuity_plan"),
        ("benefits_continuity_plan_reference", "benefits_continuity_plan"),
        ("return_to_work_plan_reference", "return_to_work_plan"),
        ("handling_policy_reference", "personal_data_handling_policy"),
        ("retention_policy_reference", "retention_policy"),
        ("requester_reference", "actor"),
        ("reviewer_reference", "actor"),
    ],
)
def test_reference_guards_reject_every_non_uuid4_through_builder_and_replace(
    field: str,
    prefix: str,
    non_v4_id: str,
) -> None:
    """Only opaque UUIDv4 suffixes satisfy the packet reference contract."""
    value = f"{prefix}:{non_v4_id}"
    builder_args = args()
    builder_args[field] = value
    with pytest.raises(ValueError, match=field):
        build_employment_leave_review_packet(**builder_args)
    with pytest.raises(ValueError, match=field):
        replace(packet(), **{field: value})


@pytest.mark.parametrize(
    "field",
    [
        "active_assignment_snapshot_digest",
        "leave_case_digest",
        "leave_policy_digest",
        "work_continuity_plan_digest",
        "benefits_continuity_plan_digest",
        "return_to_work_plan_digest",
        "handling_policy_digest",
        "retention_policy_digest",
    ],
)
def test_digest_guards(field: str) -> None:
    p = packet()
    with pytest.raises(ValueError):
        replace(p, **{field: "A" * 64})
    with pytest.raises(ValueError):
        replace(p, **{field: 1})


def test_tenant_guard_rejects_bad_noncanonical_and_sentinel_values() -> None:
    p = packet()
    for value in (
        "bad",
        "00000000-0000-0000-0000-000000000000",
        "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF",
        3,
    ):
        with pytest.raises(ValueError):
            replace(p, tenant_record_id=value)


def test_requester_and_reviewer_must_differ_syntactically() -> None:
    p = packet()
    with pytest.raises(ValueError, match="different actor references"):
        replace(p, reviewer_reference=p.requester_reference)


def test_fixed_purpose_and_allowed_non_sensitive_reason_categories() -> None:
    p = packet()
    for reason in (
        "policy_entitlement_review",
        "temporary_status_change_review",
        "operational_continuity_review",
        "return_to_work_review",
    ):
        assert replace(p, reason_code=reason).reason_code == reason
    with pytest.raises(ValueError):
        replace(p, purpose_code="employment_leave")
    for reason in ("medical_leave", "family_emergency", "depression", "free text"):
        with pytest.raises(ValueError):
            replace(p, reason_code=reason)


def test_business_dates_and_order_fail_closed() -> None:
    p = packet()
    with pytest.raises(ValueError):
        replace(p, requested_leave_start_on=datetime(2026, 9, 1, tzinfo=timezone.utc))
    with pytest.raises(ValueError):
        replace(p, requested_leave_end_on="2026-09-30")
    with pytest.raises(ValueError, match="must not precede"):
        replace(p, requested_leave_end_on=date(2026, 8, 31))


def test_single_day_leave_is_intentional_evidence() -> None:
    """Equal start/end dates record one governed single-day leave, not an error."""
    single_day = replace(
        packet(),
        requested_leave_start_on=date(2026, 9, 1),
        requested_leave_end_on=date(2026, 9, 1),
    )
    assert single_day.requested_leave_start_on == date(2026, 9, 1)
    assert single_day.requested_leave_end_on == date(2026, 9, 1)
    assert single_day.sha256_digest()


def test_timestamp_requires_aware_usable_offset_and_preserves_subseconds() -> None:
    p = packet()
    with pytest.raises(ValueError):
        replace(p, generated_at=datetime(2026, 8, 19, 2, 24, 51))

    class NullOffset(tzinfo):
        def utcoffset(self, dt: datetime | None) -> None:
            return None

        def dst(self, dt: datetime | None) -> None:
            return None

    with pytest.raises(ValueError):
        replace(p, generated_at=datetime(2026, 8, 19, tzinfo=NullOffset()))
    q = replace(p, generated_at=p.generated_at.replace(microsecond=123457))
    assert p.canonical_json() != q.canonical_json()
    assert p.sha256_digest() != q.sha256_digest()


@pytest.mark.parametrize("value", [0, -1, True, "1", 2_147_483_648])
def test_evidence_version_is_bounded_positive_integer(value: object) -> None:
    with pytest.raises(ValueError):
        replace(packet(), evidence_version=value)


def test_evidence_version_changes_digest() -> None:
    p = packet()
    q = replace(p, evidence_version=2)
    assert p.sha256_digest() != q.sha256_digest()


def test_handling_or_retention_policy_change_changes_audit_digest() -> None:
    p = packet()
    q = replace(p, handling_policy_digest="b" * 64)
    r = replace(p, retention_policy_digest="c" * 64)
    assert p.sha256_digest() != q.sha256_digest()
    assert p.sha256_digest() != r.sha256_digest()


def test_repr_redacts_personal_data_and_governance_evidence() -> None:
    p = packet()
    rendered = repr(p)

    assert rendered == "EmploymentLeaveReviewPacket(<redacted>)"
    assert p.tenant_record_id not in rendered
    assert p.person_record_reference not in rendered
    assert p.employment_record_reference not in rendered
    assert p.leave_case_reference not in rendered
    assert p.requester_reference not in rendered
    assert p.handling_policy_digest not in rendered
    assert p.requested_leave_start_on.isoformat() not in rendered


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("contains_person_pii", False),
        ("contains_medical_or_family_values", True),
        ("contains_compensation_or_benefit_values", True),
        ("contains_free_form_case_narrative", True),
        ("contains_free_form_model_output", True),
        ("human_confirmation_required", False),
        ("decision_authority", "automated"),
        ("review_state", "approved"),
        ("scope_verification_state", "verified"),
        ("mutation_state", "applied"),
        ("external_execution_state", "executed"),
        ("next_action", "approve now"),
    ],
)
def test_direct_construction_cannot_weaken_governance(field: str, value: object) -> None:
    with pytest.raises(ValueError):
        replace(packet(), **{field: value})


def test_builder_and_direct_constructor_are_equivalent() -> None:
    p = packet()
    q = EmploymentLeaveReviewPacket(**args())
    assert p == q
