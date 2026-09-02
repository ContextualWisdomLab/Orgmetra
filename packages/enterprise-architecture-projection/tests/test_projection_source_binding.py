"""Regression tests for source-revision and candidate provenance in EA projection handoffs."""

from datetime import UTC, datetime

from orgmetra_enterprise_architecture_projection import (
    ArchitectureProjectionCandidate,
    ContractAdmissionEvidence,
    ContractReleaseEvidence,
    ProjectionKind,
    evaluate_projection_readiness,
)


ORGMETRA_REPOSITORY = "ContextualWisdomLab/Orgmetra"
ORGMETRA_SHA = "9e3e4847510e1e612b48474ba42b177b8ed824df"
CONTRACT_SHA = "99d230991b9d48fbf87489e0b375b7bbf09d8559"
ARTIFACT_SHA256 = "a" * 64


def _candidate(**overrides: object) -> ArchitectureProjectionCandidate:
    """Build one valid architecture candidate with optional evidence overrides."""
    values: dict[str, object] = {
        "projection_key": "orgmetra.people-api",
        "projection_kind": ProjectionKind.APPLICATION,
        "source_revision": ORGMETRA_SHA,
        "source_repository": ORGMETRA_REPOSITORY,
        "effective_from": datetime(2026, 9, 1, tzinfo=UTC),
        "effective_to": None,
        "recorded_at": datetime(2026, 9, 1, 6, 0, tzinfo=UTC),
        "owner_reference": "team:orgmetra",
        "dependency_references": ("service:keyverse",),
    }
    values.update(overrides)
    return ArchitectureProjectionCandidate(**values)


def _release() -> ContractReleaseEvidence:
    """Build release evidence for one immutable context-graph artifact."""
    return ContractReleaseEvidence(
        repository="ContextualWisdomLab/context-graph-contracts",
        release_tag="v1.0.0",
        commit_sha=CONTRACT_SHA,
        asset_sha256=ARTIFACT_SHA256,
        release_state="published",
        verified_at=datetime(2026, 9, 1, 6, 1, tzinfo=UTC),
    )


def _admission() -> ContractAdmissionEvidence:
    """Build admission evidence bound to exact released and lifecycle evidence."""
    return ContractAdmissionEvidence(
        contract_commit_sha=CONTRACT_SHA,
        contract_asset_sha256=ARTIFACT_SHA256,
        conformance_receipt_sha256="b" * 64,
        bundle_manifest_sha256="c" * 64,
        provenance_attestation_sha256="d" * 64,
        admission_state="verified",
        verified_at=datetime(2026, 9, 1, 6, 2, tzinfo=UTC),
        compatibility_receipt_sha256="e" * 64,
        migration_receipt_sha256="f" * 64,
    )


def test_blocked_handoff_preserves_exact_orgmetra_source_identity() -> None:
    """A blocked handoff must remain attributable to the exact Orgmetra source revision."""
    decision = evaluate_projection_readiness(_candidate(), _release(), _admission())

    assert decision.ready is False
    assert decision.reason == "trusted_control_plane_evidence_not_available"
    assert decision.source_repository == ORGMETRA_REPOSITORY
    assert decision.source_revision == ORGMETRA_SHA


def test_blocked_decision_is_bound_to_exact_candidate_evidence_not_only_source_revision() -> None:
    """Two candidates from one source revision must never share transferable decision evidence."""
    first = evaluate_projection_readiness(_candidate(), _release(), _admission())
    second = evaluate_projection_readiness(
        _candidate(
            projection_key="orgmetra.people-api-secondary",
            owner_reference="application:orgmetra-people-api",
            dependency_references=("service:keyverse", "service:naruon"),
        ),
        _release(),
        _admission(),
    )

    assert first.ready is False
    assert second.ready is False
    assert first.reason == second.reason == "trusted_control_plane_evidence_not_available"
    assert first.source_revision == second.source_revision == ORGMETRA_SHA
    assert first.candidate_sha256 != second.candidate_sha256
