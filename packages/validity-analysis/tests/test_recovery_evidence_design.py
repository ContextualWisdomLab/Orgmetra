"""Regress direct-construction structural integrity for Rust recovery evidence."""

from datetime import datetime, timezone

import pytest

from orgmetra_validity_analysis import REVIEWED_FAST_MLSIRM_REVISION, RustRecoveryEvidence


COMPLETED_AT = datetime(2026, 8, 31, 11, 30, tzinfo=timezone.utc)


def recovery_evidence(**overrides: object) -> RustRecoveryEvidence:
    """Build one valid nested-multilevel aggregate recovery receipt."""
    values: dict[str, object] = {
        "evidence_reference": "validity_recovery_evidence:11111111-1111-4111-8111-111111111111",
        "request_digest": "a" * 64,
        "fast_mlsirm_revision": REVIEWED_FAST_MLSIRM_REVISION,
        "design_code": "nested_multilevel",
        "backend": "rust",
        "rust_device": "cpu",
        "model_code": "mlsirm_recovery",
        "sample_size": 48,
        "item_count": 3,
        "cluster_count": 4,
        "seed": 42,
        "convergence_status": "max_iter_reached",
        "iterations": 1,
        "objective_value": 1.0,
        "parameter_rmse_mean": 0.1,
        "latent_rmse": 0.1,
        "distance_rmse": 0.1,
        "gamma_abs_error": 0.1,
        "completed_at": COMPLETED_AT,
    }
    values.update(overrides)
    return RustRecoveryEvidence(**values)  # type: ignore[arg-type]


def test_cross_sectional_recovery_evidence_rejects_cluster_count() -> None:
    """Do not let plain cross-sectional receipts carry contradictory clusters."""
    with pytest.raises(ValueError, match="cluster_count"):
        recovery_evidence(design_code="cross_sectional", cluster_count=4)


@pytest.mark.parametrize("cluster_count", [None, 1])
def test_nested_recovery_evidence_requires_two_or_more_clusters(
    cluster_count: int | None,
) -> None:
    """Require the structural cluster evidence claimed by nested designs."""
    with pytest.raises(ValueError, match="cluster_count"):
        recovery_evidence(cluster_count=cluster_count)


def test_nested_recovery_evidence_rejects_more_clusters_than_people() -> None:
    """Reject scientifically impossible receipts with more clusters than people."""
    with pytest.raises(ValueError, match="cluster_count"):
        recovery_evidence(sample_size=2, cluster_count=3)
