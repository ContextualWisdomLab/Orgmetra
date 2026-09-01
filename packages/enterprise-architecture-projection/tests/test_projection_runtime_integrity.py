"""Runtime-integrity regressions for Enterprise Architecture projection admission."""

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


class _AlwaysEqualText(str):
    """Adversarial text whose comparison behavior lies about its stored value."""

    def __eq__(self, other: object) -> bool:
        """Claim equality with every comparison target."""
        return True

    def __ne__(self, other: object) -> bool:
        """Claim inequality with no comparison target."""
        return False


def _candidate() -> ArchitectureProjectionCandidate:
    """Return one valid projection candidate for runtime-tampering tests."""
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
    """Return valid release-shape evidence for candidate-integrity tests."""
    return ContractReleaseEvidence(
        repository="ContextualWisdomLab/context-graph-contracts",
        release_tag="v1.0.0",
        commit_sha=_CONTRACT_SHA,
        asset_sha256="a" * 64,
        release_state="published",
        verified_at=datetime(2026, 9, 1, 6, 1, tzinfo=UTC),
    )


def _admission() -> ContractAdmissionEvidence:
    """Return valid admission-shape evidence for candidate-integrity tests."""
    return ContractAdmissionEvidence(
        contract_commit_sha=_CONTRACT_SHA,
        contract_asset_sha256="a" * 64,
        conformance_receipt_sha256="b" * 64,
        bundle_manifest_sha256="c" * 64,
        provenance_attestation_sha256="d" * 64,
        admission_state="verified",
        verified_at=datetime(2026, 9, 1, 6, 2, tzinfo=UTC),
    )


def test_mutated_projection_candidate_is_revalidated_before_readiness() -> None:
    """Reject an exact candidate whose frozen fields were rewritten after construction."""
    candidate = _candidate()
    object.__setattr__(candidate, "owner_reference", "person:employee-123")

    with pytest.raises(ValueError, match="non-person architecture owner reference"):
        evaluate_projection_readiness(candidate, _release(), _admission())


def test_mutated_candidate_collection_cannot_reintroduce_mutable_evidence() -> None:
    """Reject dependency evidence rewritten to a mutable collection after construction."""
    candidate = _candidate()
    object.__setattr__(candidate, "dependency_references", ["service:keyverse"])

    with pytest.raises(ValueError, match="immutable tuple"):
        evaluate_projection_readiness(candidate, _release(), _admission())


def test_comparison_overriding_source_repository_cannot_claim_orgmetra_authority() -> None:
    """Reject behavior-bearing text that can lie about the candidate source repository."""
    candidate = _candidate()
    object.__setattr__(
        candidate,
        "source_repository",
        _AlwaysEqualText("ContextualWisdomLab/not-orgmetra"),
    )

    with pytest.raises(TypeError, match="source_repository must be exact built-in text"):
        evaluate_projection_readiness(candidate, _release(), _admission())


def test_comparison_overriding_admission_commit_cannot_bind_different_release() -> None:
    """Reject behavior-bearing digest text before exact release/admission equality checks."""
    admission = _admission()
    object.__setattr__(admission, "contract_commit_sha", _AlwaysEqualText("f" * 40))

    with pytest.raises(TypeError, match="contract_commit_sha must be exact built-in text"):
        evaluate_projection_readiness(_candidate(), _release(), admission)
