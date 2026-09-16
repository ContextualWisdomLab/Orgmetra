"""Regression tests for governed selection-validity analysis handoffs."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json

import pytest

from orgmetra_validity_analysis import (
    REVIEWED_FAST_MLSIRM_REVISION,
    ValidationAnalysisHandoff,
    build_validation_analysis_handoff,
)

TENANT = "10000000-0000-7000-8000-000000000001"
HANDOFF = "validation_analysis_handoff:11111111-1111-4111-8111-111111111111"
STUDY = "validation_study:22222222-2222-4222-8222-222222222222"
JOB = "job_profile:33333333-3333-4333-8333-333333333333"
PREDICTOR = "predictor_snapshot:44444444-4444-4444-8444-444444444444"
CRITERION = "criterion_snapshot:55555555-5555-4555-8555-555555555555"
POPULATION = "study_population_snapshot:66666666-6666-4666-8666-666666666666"
POLICY = "decision_policy:77777777-7777-4777-8777-777777777777"
PLAN = "validation_analysis_plan:88888888-8888-4888-8888-888888888888"
ACTOR = "actor:99999999-9999-4999-8999-999999999999"
REVIEWER = "actor:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
DIGEST_D = "d" * 64
DIGEST_E = "e" * 64
REQUESTED_AT = datetime(2026, 8, 21, 7, 10, 11, 123456, tzinfo=timezone(timedelta(hours=9)))


def valid_kwargs():
    """Return one complete governed handoff input fixture."""
    return {
        "tenant_record_id": TENANT,
        "handoff_reference": HANDOFF,
        "validation_study_reference": STUDY,
        "job_profile_reference": JOB,
        "predictor_snapshot_reference": PREDICTOR,
        "predictor_snapshot_digest": DIGEST_A,
        "criterion_snapshot_reference": CRITERION,
        "criterion_snapshot_digest": DIGEST_B,
        "population_snapshot_reference": POPULATION,
        "population_snapshot_digest": DIGEST_C,
        "decision_policy_reference": POLICY,
        "decision_policy_digest": DIGEST_D,
        "analysis_plan_reference": PLAN,
        "analysis_plan_digest": DIGEST_E,
        "actor_reference": ACTOR,
        "reviewer_reference": REVIEWER,
        "fast_mlsirm_revision": REVIEWED_FAST_MLSIRM_REVISION,
        "requested_at": REQUESTED_AT,
    }


def handoff():
    """Build the canonical valid handoff fixture."""
    return build_validation_analysis_handoff(**valid_kwargs())


def test_handoff_is_value_minimized_deterministic_and_human_review_only():
    """Bind exact study evidence without exposing raw person-level observations."""
    candidate = handoff()
    payload = json.loads(candidate.canonical_json())

    assert payload["tenant_record_id"] == TENANT
    assert payload["validation_study_reference"] == STUDY
    assert payload["job_profile_reference"] == JOB
    assert payload["fast_mlsirm_revision"] == REVIEWED_FAST_MLSIRM_REVISION
    assert payload["requested_at"] == "2026-08-20T22:10:11.123456Z"
    assert payload["validation_strategy"] == "criterion_related"
    assert payload["kernel_repository"] == "ContextualWisdomLab/fast-mlsirm"
    assert payload["kernel_boundary"] == "read_only_pinned_revision"
    assert payload["execution_state"] == "not_executed"
    assert payload["contains_raw_person_level_values"] is False
    assert payload["human_review_required"] is True
    assert payload["result_authority"] == "scientific_evidence_only"
    assert payload["required_result_evidence"] == [
        "effect_estimate",
        "uncertainty_interval",
        "sample_size",
        "missingness_summary",
        "convergence_diagnostics",
    ]
    assert "person_record" not in candidate.canonical_json()
    assert "candidate" not in candidate.canonical_json()
    assert repr(candidate) == "ValidationAnalysisHandoff(<redacted>)"
    assert len(candidate.sha256_digest()) == 64
    assert candidate.canonical_json() == handoff().canonical_json()


@pytest.mark.parametrize(
    "bad_tenant",
    [
        "not-a-uuid",
        "00000000-0000-0000-0000-000000000000",
        "ffffffff-ffff-ffff-ffff-ffffffffffff",
        "10000000-0000-7000-8000-00000000000A",
        1,
    ],
)
def test_tenant_identity_must_follow_protected_operational_uuid_contract(bad_tenant):
    """Reject malformed, reserved, non-canonical, and non-text tenant identities."""
    values = valid_kwargs()
    values["tenant_record_id"] = bad_tenant
    with pytest.raises(ValueError, match="tenant_record_id"):
        build_validation_analysis_handoff(**values)


@pytest.mark.parametrize(
    ("field", "bad", "match"),
    [
        ("handoff_reference", "validation_analysis_handoff:not-a-uuid", "handoff_reference"),
        ("validation_study_reference", JOB, "validation_study_reference"),
        ("job_profile_reference", "job_profile:22222222-2222-7222-8222-222222222222", "job_profile_reference"),
        ("predictor_snapshot_reference", 1, "predictor_snapshot_reference"),
        ("criterion_snapshot_reference", "criterion_snapshot:" + "a" * 161, "criterion_snapshot_reference"),
        ("population_snapshot_reference", "study_population_snapshot:not-a-uuid", "population_snapshot_reference"),
        ("decision_policy_reference", "decision_policy:BBBBBBBB-BBBB-4BBB-8BBB-BBBBBBBBBBBB", "decision_policy_reference"),
        ("analysis_plan_reference", "validation_analysis_plan:00000000-0000-0000-0000-000000000000", "analysis_plan_reference"),
        ("actor_reference", "actor:ffffffff-ffff-ffff-ffff-ffffffffffff", "actor_reference"),
        ("reviewer_reference", "actor:bbbbbbbb-bbbb-7bbb-8bbb-bbbbbbbbbbbb", "reviewer_reference"),
    ],
)
def test_all_public_references_are_namespaced_opaque_uuid4(field, bad, match):
    """Fail closed on wrong namespace, malformed, noncanonical, or non-v4 references."""
    values = valid_kwargs()
    values[field] = bad
    with pytest.raises(ValueError, match=match):
        build_validation_analysis_handoff(**values)


@pytest.mark.parametrize(
    "field",
    [
        "predictor_snapshot_digest",
        "criterion_snapshot_digest",
        "population_snapshot_digest",
        "decision_policy_digest",
        "analysis_plan_digest",
    ],
)
def test_evidence_digests_are_lowercase_sha256(field):
    """Reject weak or noncanonical evidence digests for every source snapshot."""
    values = valid_kwargs()
    values[field] = "A" * 64
    with pytest.raises(ValueError, match=field):
        build_validation_analysis_handoff(**values)


def test_requester_and_reviewer_must_be_distinct():
    """Require accountable independent interpretation instead of self-review."""
    values = valid_kwargs()
    values["reviewer_reference"] = ACTOR
    with pytest.raises(ValueError, match="different accountable actor"):
        build_validation_analysis_handoff(**values)


@pytest.mark.parametrize("bad_revision", ["not-a-sha", "A" * 40, "0" * 40])
def test_fast_mlsirm_revision_is_exactly_the_reviewed_immutable_dependency(bad_revision):
    """Reject malformed or unreviewed foreign dependency revisions."""
    values = valid_kwargs()
    values["fast_mlsirm_revision"] = bad_revision
    with pytest.raises(ValueError, match="fast_mlsirm_revision"):
        build_validation_analysis_handoff(**values)


@pytest.mark.parametrize(
    "bad_requested_at",
    [
        datetime(2026, 8, 21, 7, 10),
        "2026-08-21T07:10:00+09:00",
    ],
)
def test_requested_at_requires_an_aware_datetime(bad_requested_at):
    """Reject local-time ambiguity in immutable analysis correlation."""
    values = valid_kwargs()
    values["requested_at"] = bad_requested_at
    with pytest.raises(ValueError, match="requested_at"):
        build_validation_analysis_handoff(**values)


@pytest.mark.parametrize(
    ("field", "bad", "match"),
    [
        ("purpose_code", "other_purpose", "purpose_code"),
        ("reason_code", "other_reason", "reason_code"),
        ("evidence_version", True, "evidence_version"),
        ("evidence_version", 0, "evidence_version"),
        ("validation_strategy", "content_validity", "validation_strategy"),
        ("kernel_repository", "other/repository", "kernel_repository"),
        ("kernel_boundary", "direct_database", "kernel_boundary"),
        ("execution_state", "executed", "execution_state"),
        ("contains_raw_person_level_values", True, "raw person-level"),
        ("human_review_required", False, "human review"),
        ("result_authority", "employment_decision", "result_authority"),
        ("required_result_evidence", ("effect_estimate",), "required_result_evidence"),
        ("next_action", "Auto-approve the result.", "next_action"),
    ],
)
def test_direct_construction_cannot_weaken_governance(field, bad, match):
    """Keep fixed scientific, privacy, dependency, and human-authority semantics immutable."""
    with pytest.raises(ValueError, match=match):
        replace(handoff(), **{field: bad})


def test_codes_must_remain_bounded_descriptive_snake_case_before_fixed_value_check():
    """Exercise code-shape rejection separately from the closed purpose/reason vocabulary."""
    with pytest.raises(ValueError, match="purpose_code"):
        replace(handoff(), purpose_code="X")
    with pytest.raises(ValueError, match="reason_code"):
        replace(handoff(), reason_code="x" * 65)


def test_public_dataclass_type_is_constructible_only_with_all_invariants():
    """Document the public immutable type while preserving builder equivalence."""
    values = valid_kwargs()
    direct = ValidationAnalysisHandoff(**values)
    assert direct == handoff()
