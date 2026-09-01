"""Regression tests for source-revision provenance in EA projection handoffs."""

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


def test_ready_handoff_preserves_exact_orgmetra_source_identity() -> None:
    """A ready handoff must remain attributable to the exact Orgmetra source revision."""
    candidate = ArchitectureProjectionCandidate(
        projection_key="orgmetra.people-api",
        projection_kind=ProjectionKind.APPLICATION,
        source_revision=ORGMETRA_SHA,
        source_repository=ORGMETRA_REPOSITORY,
        effective_from=datetime(2026, 9, 1, tzinfo=UTC),
        effective_to=None,
        recorded_at=datetime(2026, 9, 1, 6, 0, tzinfo=UTC),
        owner_reference="team:orgmetra",
        dependency_references=("service:keyverse",),
    )
    release = ContractReleaseEvidence(
        repository="ContextualWisdomLab/context-graph-contracts",
        release_tag="v1.0.0",
        commit_sha=CONTRACT_SHA,
        asset_sha256=ARTIFACT_SHA256,
        release_state="published",
        verified_at=datetime(2026, 9, 1, 6, 1, tzinfo=UTC),
    )
    admission = ContractAdmissionEvidence(
        contract_commit_sha=CONTRACT_SHA,
        contract_asset_sha256=ARTIFACT_SHA256,
        conformance_receipt_sha256="b" * 64,
        bundle_manifest_sha256="c" * 64,
        provenance_attestation_sha256="d" * 64,
        admission_state="verified",
        verified_at=datetime(2026, 9, 1, 6, 2, tzinfo=UTC),
    )

    decision = evaluate_projection_readiness(candidate, release, admission)

    assert decision.ready is True
    assert decision.source_repository == ORGMETRA_REPOSITORY
    assert decision.source_revision == ORGMETRA_SHA
