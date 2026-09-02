"""Compatibility and migration admission regressions for EA projections."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from orgmetra_enterprise_architecture_projection import (
    ArchitectureProjectionCandidate,
    ContractAdmissionEvidence,
    ContractReleaseEvidence,
    ProjectionKind,
    evaluate_projection_readiness,
)


_ORGMETRA_SHA = "9e3e4847510e1e612b48474ba42b177b8ed824df"
_CONTRACT_SHA = "99d230991b9d48fbf87489e0b375b7bbf09d8559"
_ARTIFACT_SHA256 = "a" * 64
_COMPATIBILITY_SHA256 = "e" * 64
_MIGRATION_SHA256 = "f" * 64


def _candidate() -> ArchitectureProjectionCandidate:
    """Return a valid deployable-architecture candidate."""
    return ArchitectureProjectionCandidate(
        projection_key="orgmetra.people-api",
        projection_kind=ProjectionKind.APPLICATION,
        source_revision=_ORGMETRA_SHA,
        source_repository="ContextualWisdomLab/Orgmetra",
        effective_from=datetime(2026, 9, 1, tzinfo=UTC),
        effective_to=None,
        recorded_at=datetime(2026, 9, 1, 6, 0, tzinfo=UTC),
        owner_reference="team:orgmetra",
        dependency_references=("service:keyverse",),
    )


def _release() -> ContractReleaseEvidence:
    """Return exact immutable release identity for admission tests."""
    return ContractReleaseEvidence(
        repository="ContextualWisdomLab/context-graph-contracts",
        release_tag="v1.0.0",
        commit_sha=_CONTRACT_SHA,
        asset_sha256=_ARTIFACT_SHA256,
        release_state="published",
        verified_at=datetime(2026, 9, 1, 6, 1, tzinfo=UTC),
    )


def _legacy_admission() -> ContractAdmissionEvidence:
    """Return semantic admission that lacks lifecycle compatibility evidence."""
    return ContractAdmissionEvidence(
        contract_commit_sha=_CONTRACT_SHA,
        contract_asset_sha256=_ARTIFACT_SHA256,
        conformance_receipt_sha256="b" * 64,
        bundle_manifest_sha256="c" * 64,
        provenance_attestation_sha256="d" * 64,
        admission_state="verified",
        verified_at=datetime(2026, 9, 1, 6, 2, tzinfo=UTC),
    )


def _admission(**overrides: object) -> ContractAdmissionEvidence:
    """Return release-bound evidence including compatibility and migration receipts."""
    values: dict[str, object] = {
        "contract_commit_sha": _CONTRACT_SHA,
        "contract_asset_sha256": _ARTIFACT_SHA256,
        "conformance_receipt_sha256": "b" * 64,
        "bundle_manifest_sha256": "c" * 64,
        "provenance_attestation_sha256": "d" * 64,
        "admission_state": "verified",
        "verified_at": datetime(2026, 9, 1, 6, 2, tzinfo=UTC),
        "compatibility_receipt_sha256": _COMPATIBILITY_SHA256,
        "migration_receipt_sha256": _MIGRATION_SHA256,
    }
    values.update(overrides)
    return ContractAdmissionEvidence(**values)


def test_semantic_admission_without_lifecycle_receipts_remains_blocked() -> None:
    """Do not mistake conformance and provenance for consumer compatibility."""
    decision = evaluate_projection_readiness(
        _candidate(),
        _release(),
        _legacy_admission(),
    )

    assert decision.ready is False
    assert decision.reason == "context_graph_contract_lifecycle_evidence_not_verified"
    assert decision.next_action == "verify_context_graph_contract_compatibility_and_migration"
    assert decision.contract_compatibility_receipt_sha256 is None
    assert decision.contract_migration_receipt_sha256 is None


@pytest.mark.parametrize(
    ("field", "retained_compatibility", "retained_migration"),
    [
        ("compatibility_receipt_sha256", None, _MIGRATION_SHA256),
        ("migration_receipt_sha256", _COMPATIBILITY_SHA256, None),
    ],
)
def test_each_missing_lifecycle_receipt_blocks_projection_independently(
    field: str,
    retained_compatibility: str | None,
    retained_migration: str | None,
) -> None:
    """Require both lifecycle receipts instead of accepting whichever one exists."""
    decision = evaluate_projection_readiness(
        _candidate(),
        _release(),
        _admission(**{field: None}),
    )

    assert decision.ready is False
    assert decision.reason == "context_graph_contract_lifecycle_evidence_not_verified"
    assert decision.next_action == "verify_context_graph_contract_compatibility_and_migration"
    assert decision.contract_compatibility_receipt_sha256 == retained_compatibility
    assert decision.contract_migration_receipt_sha256 == retained_migration


def test_one_lifecycle_receipt_cannot_stand_in_for_both_results() -> None:
    """Reject duplicated receipt identity across compatibility and migration evidence."""
    with pytest.raises(ValueError, match="distinct lifecycle evidence"):
        evaluate_projection_readiness(
            _candidate(),
            _release(),
            _admission(migration_receipt_sha256=_COMPATIBILITY_SHA256),
        )


def test_admission_verification_cannot_predate_release_verification() -> None:
    """Reject lifecycle evidence that was allegedly verified before release identity."""
    with pytest.raises(ValueError, match="cannot predate release verification"):
        evaluate_projection_readiness(
            _candidate(),
            _release(),
            _admission(verified_at=datetime(2026, 9, 1, 6, 0, tzinfo=UTC)),
        )


def test_shape_complete_projection_retains_receipts_but_stays_blocked() -> None:
    """Retain lifecycle evidence without authorizing caller-created external evidence."""
    decision = evaluate_projection_readiness(_candidate(), _release(), _admission())

    assert decision.ready is False
    assert decision.reason == "trusted_control_plane_evidence_not_available"
    assert decision.next_action == "integrate_released_context_graph_trust_contract"
    assert decision.contract_compatibility_receipt_sha256 == _COMPATIBILITY_SHA256
    assert decision.contract_migration_receipt_sha256 == _MIGRATION_SHA256


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("compatibility_receipt_sha256", "compatibility receipt SHA-256"),
        ("migration_receipt_sha256", "migration receipt SHA-256"),
    ],
)
def test_malformed_compatibility_or_migration_receipt_is_rejected(
    field: str,
    message: str,
) -> None:
    """Reject release admission whose lifecycle evidence is not digest-bound."""
    with pytest.raises(ValueError, match=message):
        evaluate_projection_readiness(
            _candidate(),
            _release(),
            _admission(**{field: "not-a-sha256"}),
        )
