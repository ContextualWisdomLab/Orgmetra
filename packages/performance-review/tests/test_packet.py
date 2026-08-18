from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json

import pytest

from orgmetra_performance_review import (
    PerformanceReviewPacket,
    build_performance_review_packet,
)

TENANT = "11111111-1111-4111-8111-111111111111"
PERFORMANCE_REVIEW = "performance_review:22222222-2222-4222-8222-222222222222"
PERSON = "person_record:33333333-3333-4333-8333-333333333333"
EMPLOYMENT = "employment_record:44444444-4444-4444-8444-444444444444"
JOB = "job_profile:55555555-5555-4555-8555-555555555555"
CYCLE = "performance_cycle:66666666-6666-4666-8666-666666666666"
CRITERION_SET = "criterion_set:77777777-7777-4777-8777-777777777777"
GOAL_PLAN = "performance_goal_plan:88888888-8888-4888-8888-888888888888"
OBSERVATION_SNAPSHOT = "criterion_observation_snapshot:99999999-9999-4999-8999-999999999999"
DEVELOPMENT_PLAN = "development_plan:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
REVIEWER = "actor:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
DIGEST_D = "d" * 64
GENERATED_AT = datetime(2026, 8, 19, 5, 15, 30, 123456, tzinfo=timezone.utc)


def build_valid(**overrides: object) -> PerformanceReviewPacket:
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "performance_review_reference": PERFORMANCE_REVIEW,
        "person_record_reference": PERSON,
        "employment_record_reference": EMPLOYMENT,
        "job_profile_reference": JOB,
        "performance_cycle_reference": CYCLE,
        "criterion_set_reference": CRITERION_SET,
        "criterion_set_digest": DIGEST_A,
        "goal_plan_reference": GOAL_PLAN,
        "goal_plan_digest": DIGEST_B,
        "criterion_observation_snapshot_reference": OBSERVATION_SNAPSHOT,
        "criterion_observation_snapshot_digest": DIGEST_C,
        "development_plan_reference": DEVELOPMENT_PLAN,
        "development_plan_digest": DIGEST_D,
        "reviewer_reference": REVIEWER,
        "purpose_code": "performance_review",
        "reason_code": "scheduled_cycle_review",
        "review_period_start": date(2026, 1, 1),
        "review_period_end": date(2026, 6, 30),
        "generated_at": GENERATED_AT,
    }
    values.update(overrides)
    return build_performance_review_packet(**values)


def test_builds_value_free_human_review_packet() -> None:
    packet = build_valid()
    assert packet.contains_person_pii is False
    assert packet.contains_rating_value is False
    assert packet.contains_free_form_model_output is False
    assert packet.human_confirmation_required is True
    assert packet.decision_authority == "human_review_only"
    assert packet.review_state == "requires_human_review"
    assert "record accountable human rating and feedback" in packet.next_action


def test_canonical_json_and_digest_are_deterministic() -> None:
    packet = build_valid()
    canonical = packet.canonical_json()
    payload = json.loads(canonical)
    assert payload["person_record_reference"] == PERSON
    assert payload["generated_at"] == "2026-08-19T05:15:30.123456Z"
    assert packet.sha256_digest() == sha256(canonical.encode("utf-8")).hexdigest()
    assert canonical == build_valid().canonical_json()


def test_timestamp_normalizes_to_utc_without_losing_precision() -> None:
    shifted = GENERATED_AT.astimezone(timezone(timedelta(hours=9)))
    assert build_valid(generated_at=shifted).canonical_json() == build_valid().canonical_json()
    later = build_valid(generated_at=GENERATED_AT.replace(microsecond=123457))
    assert later.canonical_json() != build_valid().canonical_json()
    assert later.sha256_digest() != build_valid().sha256_digest()


def test_optional_development_plan_may_be_absent_as_a_pair() -> None:
    packet = build_valid(development_plan_reference=None, development_plan_digest=None)
    assert packet.development_plan_reference is None
    assert packet.development_plan_digest is None


@pytest.mark.parametrize("tenant", ["not-a-uuid", "00000000-0000-0000-0000-000000000000", "11111111-1111-4111-8111-11111111111A", None])
def test_rejects_noncanonical_tenant_identity(tenant: object) -> None:
    with pytest.raises(ValueError, match="tenant_record_id"):
        build_valid(tenant_record_id=tenant)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("performance_review_reference", "performance_review:Jane-Doe"),
        ("person_record_reference", "candidate_profile:33333333-3333-4333-8333-333333333333"),
        ("employment_record_reference", "employment_record:00000000-0000-0000-0000-000000000000"),
        ("job_profile_reference", "job_profile:not-a-uuid"),
        ("performance_cycle_reference", "performance_cycle:66666666-6666-4666-8666-66666666666A"),
        ("criterion_set_reference", "criterion:77777777-7777-4777-8777-777777777777"),
        ("goal_plan_reference", "performance_goal_plan:salary"),
        ("criterion_observation_snapshot_reference", "criterion_observation_snapshot:score-4"),
        ("reviewer_reference", "actor:reviewer-name"),
    ],
)
def test_rejects_nonopaque_or_wrong_namespace_references(field: str, value: str) -> None:
    with pytest.raises(ValueError, match=field):
        build_valid(**{field: value})


@pytest.mark.parametrize("field", ["criterion_set_digest", "goal_plan_digest", "criterion_observation_snapshot_digest", "development_plan_digest"])
def test_rejects_malformed_evidence_digests(field: str) -> None:
    with pytest.raises(ValueError, match=field):
        build_valid(**{field: "ABC"})


def test_requires_development_reference_and_digest_as_a_pair() -> None:
    with pytest.raises(ValueError, match="development plan reference and digest"):
        build_valid(development_plan_reference=None)
    with pytest.raises(ValueError, match="development plan reference and digest"):
        build_valid(development_plan_digest=None)


@pytest.mark.parametrize("purpose", ["selection_review", "performance", "Performance_Review"])
def test_purpose_is_fixed(purpose: str) -> None:
    with pytest.raises(ValueError, match="purpose_code must remain performance_review"):
        build_valid(purpose_code=purpose)


@pytest.mark.parametrize("reason", ["singleword", "Upper_case", "a" * 65])
def test_reason_code_is_bounded_descriptive_snake_case(reason: str) -> None:
    with pytest.raises(ValueError, match="reason_code"):
        build_valid(reason_code=reason)


def test_review_period_must_be_real_dates_in_order() -> None:
    with pytest.raises(ValueError, match="review_period_start"):
        build_valid(review_period_start="2026-01-01")
    with pytest.raises(ValueError, match="review_period_end"):
        build_valid(review_period_end="2026-06-30")
    with pytest.raises(ValueError, match="review period"):
        build_valid(review_period_start=date(2026, 7, 1), review_period_end=date(2026, 6, 30))


@pytest.mark.parametrize("generated_at", [datetime(2026, 8, 19, 5, 15), "2026-08-19T05:15:00Z"])
def test_generated_at_must_be_timezone_aware_datetime(generated_at: object) -> None:
    with pytest.raises(ValueError, match="generated_at"):
        build_valid(generated_at=generated_at)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("contains_person_pii", True, "must not contain person PII"),
        ("contains_rating_value", True, "must not contain rating values"),
        ("contains_free_form_model_output", True, "must not contain free-form model output"),
        ("human_confirmation_required", 1, "human confirmation is mandatory"),
        ("decision_authority", "model_decision", "decision_authority"),
        ("review_state", "approved", "review_state"),
        ("next_action", "Auto-rate the employee.", "next_action"),
    ],
)
def test_direct_construction_cannot_weaken_governance(field: str, value: object, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        replace(build_valid(), **{field: value})


def test_direct_construction_revalidates_reference_and_digest() -> None:
    with pytest.raises(ValueError, match="person_record_reference"):
        replace(build_valid(), person_record_reference="person_record:Jane-Doe")
    with pytest.raises(ValueError, match="criterion_set_digest"):
        replace(build_valid(), criterion_set_digest="0" * 63)


def test_builder_returns_same_public_type_as_direct_contract() -> None:
    packet = build_valid()
    assert isinstance(packet, PerformanceReviewPacket)
