"""Regressions for authoritative requester/reviewer identity separation."""

from datetime import datetime, timezone

from orgmetra_validity_analysis import (
    REVIEWED_FAST_MLSIRM_REVISION,
    build_validation_analysis_handoff,
)


def test_next_action_requires_resolved_actor_identity_separation() -> None:
    """Do not let different opaque actor references masquerade as distinct people."""
    handoff = build_validation_analysis_handoff(
        tenant_record_id="10000000-0000-7000-8000-000000000001",
        handoff_reference="validation_analysis_handoff:11111111-1111-4111-8111-111111111111",
        validation_study_reference="validation_study:22222222-2222-4222-8222-222222222222",
        job_profile_reference="job_profile:33333333-3333-4333-8333-333333333333",
        predictor_snapshot_reference="predictor_snapshot:44444444-4444-4444-8444-444444444444",
        predictor_snapshot_digest="a" * 64,
        criterion_snapshot_reference="criterion_snapshot:55555555-5555-4555-8555-555555555555",
        criterion_snapshot_digest="b" * 64,
        population_snapshot_reference="study_population_snapshot:66666666-6666-4666-8666-666666666666",
        population_snapshot_digest="c" * 64,
        decision_policy_reference="decision_policy:77777777-7777-4777-8777-777777777777",
        decision_policy_digest="d" * 64,
        analysis_plan_reference="validation_analysis_plan:88888888-8888-4888-8888-888888888888",
        analysis_plan_digest="e" * 64,
        actor_reference="actor:99999999-9999-4999-8999-999999999999",
        reviewer_reference="actor:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        fast_mlsirm_revision=REVIEWED_FAST_MLSIRM_REVISION,
        requested_at=datetime(2026, 8, 21, 1, 0, tzinfo=timezone.utc),
    )

    assert "prove requester and reviewer resolve to distinct authoritative actor identities" in handoff.next_action
