"""Regression coverage for selection-validity temporal evidence integrity."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from orgmetra_validity_analysis import (
    ConvergenceDiagnostics,
    MissingnessSummary,
    REVIEWED_FAST_MLSIRM_REVISION,
    ValidationAnalysisResult,
    build_validation_analysis_handoff,
)


class ForgedDateTime(datetime):
    """Datetime subclass able to forge canonical validation evidence."""

    def astimezone(self, tz=None):  # type: ignore[no-untyped-def]
        """Keep the hostile subclass alive across UTC normalization."""
        return self

    def isoformat(self, *args, **kwargs) -> str:  # type: ignore[no-untyped-def]
        """Return an instant different from the underlying evidence instant."""
        return "2099-12-31T23:59:59+00:00"


def test_handoff_rejects_datetime_subclass_that_can_forge_requested_at() -> None:
    """Handoff canonical evidence must not invoke caller-overridable datetime methods."""
    with pytest.raises(ValueError, match="requested_at"):
        build_validation_analysis_handoff(
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
            requested_at=ForgedDateTime(2026, 8, 21, 4, 45, tzinfo=timezone.utc),
        )


def test_result_rejects_datetime_subclass_that_can_forge_completed_at() -> None:
    """Result canonical evidence must not invoke caller-overridable datetime methods."""
    with pytest.raises(ValueError, match="requested_at"):
        ValidationAnalysisResult(
            tenant_record_id="10000000-0000-7000-8000-000000000001",
            result_reference="validation_analysis_result:11111111-1111-4111-8111-111111111111",
            handoff_digest="a" * 64,
            provenance_digest="b" * 64,
            fast_mlsirm_revision=REVIEWED_FAST_MLSIRM_REVISION,
            model_code="mlsirm_criterion_related",
            backend="rust_cpu",
            precision="f64",
            effect_estimate=0.42,
            uncertainty_lower=0.10,
            uncertainty_upper=0.70,
            sample_size=12,
            missingness_summary=MissingnessSummary(
                total_observations=12,
                complete_observations=10,
                missing_predictor_observations=1,
                missing_criterion_observations=1,
            ),
            convergence_diagnostics=ConvergenceDiagnostics(
                converged=True,
                iterations=42,
                objective_value=-12.5,
                maximum_gradient=0.0001,
            ),
            completed_at=ForgedDateTime(2026, 8, 21, 4, 45, tzinfo=timezone.utc),
        )
