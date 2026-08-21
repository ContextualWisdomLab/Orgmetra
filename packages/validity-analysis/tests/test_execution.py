"""Test the governed Rust execution request and recovery evidence contracts."""

from datetime import datetime, timezone
from dataclasses import replace
import json

import pytest

from orgmetra_validity_analysis import (
    REVIEWED_FAST_MLSIRM_REVISION,
    RustExecutionRequest,
    RustRecoveryEvidence,
    UnsupportedExecutionDesign,
    build_rust_recovery_evidence,
)


EXECUTION = "validity_execution:11111111-1111-4111-8111-111111111111"
HANDOFF_DIGEST = "a" * 64
DATASET_DIGEST = "b" * 64
COMPLETED_AT = datetime(2026, 8, 21, 7, 10, 11, 123456, tzinfo=timezone.utc)


def request(**overrides: object) -> RustExecutionRequest:
    """Build one valid nested multilevel execution request."""
    values: dict[str, object] = {
        "execution_reference": EXECUTION,
        "handoff_digest": HANDOFF_DIGEST,
        "dataset_digest": DATASET_DIGEST,
        "fast_mlsirm_revision": REVIEWED_FAST_MLSIRM_REVISION,
        "design_code": "nested_multilevel",
        "sample_size": 48,
        "item_count": 3,
        "seed": 42,
        "cluster_count": 4,
        "occasion_count": 1,
        "maximum_memberships": 1,
        "worker_count": 4,
    }
    values.update(overrides)
    return RustExecutionRequest(**values)


def worker_output(**overrides: object) -> dict[str, object]:
    """Build one aggregate response matching the pinned worker smoke run."""
    values: dict[str, object] = {
        "model": "MLS2PLM",
        "backend": "rust",
        "rust_device": "cpu",
        "status": "max_iter_reached",
        "n_iter": 1,
        "objective": 61.86235830761439,
        "n_persons": 48,
        "n_items": 3,
        "n_clusters": 4,
        "recovery_summary": {
            "parameter_rmse_mean": 0.9038215324094603,
            "latent_rmse": 0.7660918765097591,
            "distance_rmse": 1.0155729963825437,
            "gamma_abs_error": 0.9304347321005841,
        },
    }
    values.update(overrides)
    return values


def test_request_and_recovery_are_deterministic_and_redacted() -> None:
    """Serialize only aggregate evidence and bind it to the request digest."""
    candidate = request()
    evidence = build_rust_recovery_evidence(
        candidate, worker_output(), completed_at=COMPLETED_AT
    )

    request_payload = json.loads(candidate.canonical_json())
    evidence_payload = json.loads(evidence.canonical_json())
    assert request_payload["design_code"] == "nested_multilevel"
    assert request_payload["runnable"] is True
    assert evidence_payload["request_digest"] == candidate.sha256_digest()
    assert evidence_payload["result_authority"] == "scientific_evidence_only"
    assert evidence_payload["execution_state"] == "completed"
    assert "person_record" not in evidence.canonical_json()
    assert repr(candidate) == "RustExecutionRequest(<redacted>)"
    assert repr(evidence) == "RustRecoveryEvidence(<redacted>)"
    assert len(evidence.sha256_digest()) == 64
    assert evidence.canonical_json() == build_rust_recovery_evidence(
        candidate, worker_output(), completed_at=COMPLETED_AT
    ).canonical_json()


def test_cross_sectional_request_is_runnable_without_clusters() -> None:
    """Allow the pinned worker's plain cross-sectional design."""
    candidate = request(
        design_code="cross_sectional",
        cluster_count=None,
    )
    assert candidate.runnable is True
    candidate.require_runnable()
    evidence = build_rust_recovery_evidence(
        candidate,
        worker_output(n_clusters=None),
        completed_at=COMPLETED_AT,
    )
    assert evidence.cluster_count is None


@pytest.mark.parametrize(
    ("design_code", "overrides"),
    [
        ("multiple_membership", {"maximum_memberships": 2, "cluster_count": None}),
        ("longitudinal", {"occasion_count": 2, "cluster_count": None}),
    ],
)
def test_contract_only_designs_fail_closed(
    design_code: str, overrides: dict[str, object]
) -> None:
    """Keep multiple-membership and longitudinal contracts non-executable."""
    candidate = request(design_code=design_code, **overrides)
    assert candidate.runnable is False
    with pytest.raises(UnsupportedExecutionDesign, match=design_code):
        candidate.require_runnable()
    with pytest.raises(UnsupportedExecutionDesign, match=design_code):
        build_rust_recovery_evidence(candidate, worker_output(), completed_at=COMPLETED_AT)


def test_multiple_membership_rejects_cluster_metadata() -> None:
    """Keep multiple-membership structure explicit rather than conflating clusters."""
    with pytest.raises(ValueError, match="cluster_count"):
        request(
            design_code="multiple_membership",
            maximum_memberships=2,
            cluster_count=4,
        )


def test_gpu_provenance_is_preserved_when_worker_reports_gpu() -> None:
    """Preserve actual GPU provenance without asserting parity or availability."""
    candidate = request(rust_device="gpu")
    evidence = build_rust_recovery_evidence(
        candidate,
        worker_output(rust_device="gpu"),
        completed_at=COMPLETED_AT,
    )
    assert evidence.rust_device == "gpu"


@pytest.mark.parametrize(
    "field, value",
    [
        ("execution_reference", "wrong:11111111-1111-4111-8111-111111111111"),
        ("execution_reference", "validity_execution:111111111111111111111111111111111111"),
        ("execution_reference", "validity_execution:11111111-1111-1111-8111-111111111111"),
        ("fast_mlsirm_revision", "0" * 40),
        ("handoff_digest", "bad"),
        ("dataset_digest", "bad"),
        ("design_code", "unsupported_design"),
        ("sample_size", 0),
        ("item_count", 0),
        ("seed", -1),
        ("worker_count", 0),
        ("backend", "numpy"),
        ("rust_device", "tpu"),
    ],
)
def test_request_rejects_malformed_governance_fields(field: str, value: object) -> None:
    """Reject malformed execution identity, dimensions, and backend fields."""
    with pytest.raises(ValueError):
        request(**{field: value})


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"cluster_count": None}, "cluster_count"),
        ({"cluster_count": 1}, "cluster_count"),
        ({"occasion_count": 2}, "occasion_count"),
        ({"maximum_memberships": 2}, "maximum_memberships"),
    ],
)
def test_request_rejects_inconsistent_nested_design(
    overrides: dict[str, object], message: str
) -> None:
    """Reject nested designs whose structural dimensions do not agree."""
    with pytest.raises(ValueError, match=message):
        request(**overrides)


def test_request_rejects_cross_sectional_extra_structure() -> None:
    """Reject cluster, longitudinal, and membership metadata on plain designs."""
    with pytest.raises(ValueError, match="cluster_count"):
        request(design_code="cross_sectional", cluster_count=4)
    with pytest.raises(ValueError, match="occasion_count"):
        request(design_code="cross_sectional", cluster_count=None, occasion_count=2)
    with pytest.raises(ValueError, match="maximum_memberships"):
        request(design_code="cross_sectional", cluster_count=None, maximum_memberships=2)


def test_longitudinal_and_multiple_membership_contracts_validate_their_minimums() -> None:
    """Reject contract-only designs that omit the structure they claim."""
    with pytest.raises(ValueError, match="occasion_count"):
        request(design_code="longitudinal", cluster_count=None)
    with pytest.raises(ValueError, match="maximum_memberships"):
        request(design_code="multiple_membership", cluster_count=None)


@pytest.mark.parametrize(
    "override",
    [
        {"model": "other"},
        {"backend": "numpy"},
        {"rust_device": "gpu"},
        {"status": "unknown"},
        {"status": []},
        {"n_iter": 0},
        {"objective": float("nan")},
        {"objective": "not-a-number"},
        {"n_persons": 47},
        {"n_items": 2},
        {"n_clusters": 3},
        {
            "recovery_summary": {
                "parameter_rmse_mean": 0.1,
                "latent_rmse": 0.2,
                "distance_rmse": 0.3,
            }
        },
        {
            "recovery_summary": {
                "parameter_rmse_mean": -0.1,
                "latent_rmse": 0.2,
                "distance_rmse": 0.3,
                "gamma_abs_error": 0.4,
            }
        },
    ],
)
def test_builder_rejects_untrusted_worker_output(override: dict[str, object]) -> None:
    """Reject worker responses that drift from the reviewed aggregate schema."""
    with pytest.raises((ValueError, KeyError)):
        build_rust_recovery_evidence(
            request(), worker_output(**override), completed_at=COMPLETED_AT
        )


def test_builder_rejects_unknown_and_non_mapping_worker_output() -> None:
    """Reject output containers that could hide unreviewed evidence fields."""
    with pytest.raises(ValueError, match="mapping"):
        build_rust_recovery_evidence(request(), [], completed_at=COMPLETED_AT)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="fields"):
        build_rust_recovery_evidence(
            request(), {**worker_output(), "person_record": "secret"}, completed_at=COMPLETED_AT
        )
    with pytest.raises(ValueError, match="mapping"):
        build_rust_recovery_evidence(
            request(), worker_output(recovery_summary=[]), completed_at=COMPLETED_AT
        )


def test_builder_rejects_wrong_completed_at_and_result_identity() -> None:
    """Reject naive completion times and mismatched worker provenance."""
    with pytest.raises(ValueError, match="timezone"):
        build_rust_recovery_evidence(request(), worker_output(), completed_at=datetime.now())
    with pytest.raises(ValueError, match="backend"):
        build_rust_recovery_evidence(
            request(), worker_output(backend="numpy"), completed_at=COMPLETED_AT
        )
    with pytest.raises(ValueError, match="rust_device"):
        build_rust_recovery_evidence(
            request(), worker_output(rust_device="gpu"), completed_at=COMPLETED_AT
        )


def test_evidence_constructor_rejects_unlinked_result() -> None:
    """Require evidence to carry a real request digest and exact governed fields."""
    with pytest.raises(ValueError, match="request_digest"):
        RustRecoveryEvidence(
            evidence_reference="validity_recovery_evidence:11111111-1111-4111-8111-111111111111",
            request_digest="bad",
            fast_mlsirm_revision=REVIEWED_FAST_MLSIRM_REVISION,
            design_code="nested_multilevel",
            backend="rust",
            rust_device="cpu",
            model_code="mlsirm_recovery",
            sample_size=48,
            item_count=3,
            cluster_count=4,
            seed=42,
            convergence_status="max_iter_reached",
            iterations=1,
            objective_value=1.0,
            parameter_rmse_mean=0.1,
            latent_rmse=0.1,
            distance_rmse=0.1,
            gamma_abs_error=0.1,
            completed_at=COMPLETED_AT,
        )


def test_evidence_rejects_governance_drift_after_worker_build() -> None:
    """Keep direct construction as strict as the worker adapter."""
    evidence = build_rust_recovery_evidence(
        request(), worker_output(), completed_at=COMPLETED_AT
    )
    invalid = [
        ("fast_mlsirm_revision", "0" * 40),
        ("design_code", "multiple_membership"),
        ("backend", "numpy"),
        ("rust_device", "tpu"),
        ("model_code", "other_model"),
        ("cluster_count", 0),
        ("convergence_status", "failed"),
        ("result_authority", "employment_decision"),
        ("execution_state", "not_executed"),
        ("contains_raw_person_level_values", True),
        ("human_review_required", False),
    ]
    for field, value in invalid:
        with pytest.raises(ValueError):
            replace(evidence, **{field: value})


def test_evidence_accepts_cross_sectional_without_cluster_count() -> None:
    """Keep the optional cluster field absent for a plain runnable design."""
    evidence = build_rust_recovery_evidence(
        request(design_code="cross_sectional", cluster_count=None),
        worker_output(n_clusters=None),
        completed_at=COMPLETED_AT,
    )
    assert evidence.cluster_count is None
