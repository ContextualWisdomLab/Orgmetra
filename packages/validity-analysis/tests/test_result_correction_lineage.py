"""Regression tests for append-only validation-result correction lineage."""

from datetime import datetime, timezone
import json

import pytest

from orgmetra_validity_analysis import (
    ConvergenceDiagnostics,
    MissingnessSummary,
    REVIEWED_FAST_MLSIRM_REVISION,
    ValidationAnalysisResult,
)

TENANT = "10000000-0000-7000-8000-000000000001"
RESULT = "validation_analysis_result:11111111-1111-4111-8111-111111111111"
SUCCESSOR_RESULT = "validation_analysis_result:22222222-2222-4222-8222-222222222222"
COMPLETED_AT = datetime(2026, 9, 17, 12, 30, tzinfo=timezone.utc)


def _result(**overrides: object) -> ValidationAnalysisResult:
    """Build one valid aggregate-only result envelope."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "result_reference": RESULT,
        "handoff_digest": "a" * 64,
        "provenance_digest": "b" * 64,
        "fast_mlsirm_revision": REVIEWED_FAST_MLSIRM_REVISION,
        "model_code": "mlsirm_criterion_related",
        "backend": "rust_cpu",
        "precision": "f64",
        "effect_estimate": 0.42,
        "uncertainty_lower": 0.10,
        "uncertainty_upper": 0.70,
        "sample_size": 12,
        "missingness_summary": MissingnessSummary(
            total_observations=12,
            complete_observations=10,
            missing_predictor_observations=1,
            missing_criterion_observations=1,
        ),
        "convergence_diagnostics": ConvergenceDiagnostics(
            converged=True,
            iterations=42,
            objective_value=-12.5,
            maximum_gradient=0.0001,
        ),
        "completed_at": COMPLETED_AT,
    }
    values.update(overrides)
    return ValidationAnalysisResult(**values)


def test_successor_result_binds_exact_predecessor_evidence() -> None:
    """Serialize correction sequence and exact predecessor identity into result bytes."""
    predecessor = _result()
    successor = _result(
        result_reference=SUCCESSOR_RESULT,
        correction_sequence=2,
        supersedes_result_reference=predecessor.result_reference,
        supersedes_result_digest=predecessor.sha256_digest(),
        effect_estimate=0.48,
    )

    payload = json.loads(successor.canonical_json())
    assert payload["correction_sequence"] == 2
    assert payload["supersedes_result_reference"] == predecessor.result_reference
    assert payload["supersedes_result_digest"] == predecessor.sha256_digest()
    assert successor.sha256_digest() != predecessor.sha256_digest()


def test_initial_result_rejects_predecessor_coordinates() -> None:
    """Do not let sequence-one evidence pretend to supersede another result."""
    with pytest.raises(ValueError, match="correction_sequence 1"):
        _result(
            supersedes_result_reference=SUCCESSOR_RESULT,
            supersedes_result_digest="c" * 64,
        )


@pytest.mark.parametrize(
    "overrides",
    [
        {"correction_sequence": True},
        {"correction_sequence": 0},
        {"correction_sequence": 2},
        {
            "correction_sequence": 2,
            "supersedes_result_reference": SUCCESSOR_RESULT,
        },
        {
            "correction_sequence": 2,
            "supersedes_result_digest": "c" * 64,
        },
        {
            "correction_sequence": 2,
            "supersedes_result_reference": RESULT,
            "supersedes_result_digest": "c" * 64,
        },
        {
            "correction_sequence": 2,
            "supersedes_result_reference": "analysis_weight_receipt:22222222-2222-4222-8222-222222222222",
            "supersedes_result_digest": "c" * 64,
        },
        {
            "correction_sequence": 2,
            "supersedes_result_reference": SUCCESSOR_RESULT,
            "supersedes_result_digest": "not-a-digest",
        },
    ],
)
def test_malformed_result_correction_lineage_fails_closed(
    overrides: dict[str, object],
) -> None:
    """Reject ambiguous, cyclic-looking, or malformed correction coordinates."""
    with pytest.raises(ValueError):
        _result(**overrides)
