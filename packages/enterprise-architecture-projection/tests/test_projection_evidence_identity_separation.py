"""Regression tests for semantic separation of EA admission evidence identities."""

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


ORGMETRA_SHA = "9e3e4847510e1e612b48474ba42b177b8ed824df"
CONTRACT_SHA = "99d230991b9d48fbf87489e0b375b7bbf09d8559"
ARTIFACT_SHA256 = "a" * 64
CONFORMANCE_SHA256 = "b" * 64
BUNDLE_SHA256 = "c" * 64
PROVENANCE_SHA256 = "d" * 64
COMPATIBILITY_SHA256 = "e" * 64
MIGRATION_SHA256 = "f" * 64


def _candidate() -> ArchitectureProjectionCandidate:
    """Return one deployable architecture candidate with no HR record payload."""
    return ArchitectureProjectionCandidate(
        projection_key="orgmetra.people-api",
        projection_kind=ProjectionKind.APPLICATION,
        source_revision=ORGMETRA_SHA,
        source_repository="ContextualWisdomLab/Orgmetra",
        effective_from=datetime(2026, 9, 1, tzinfo=UTC),
        effective_to=None,
        recorded_at=datetime(2026, 9, 1, 6, 0, tzinfo=UTC),
        owner_reference="team:orgmetra",
        dependency_references=("service:keyverse",),
    )


def _release() -> ContractReleaseEvidence:
    """Return one immutable published Context Graph release identity."""
    return ContractReleaseEvidence(
        repository="ContextualWisdomLab/context-graph-contracts",
        release_tag="v1.0.0",
        commit_sha=CONTRACT_SHA,
        asset_sha256=ARTIFACT_SHA256,
        release_state="published",
        verified_at=datetime(2026, 9, 1, 6, 1, tzinfo=UTC),
    )


def _admission(**overrides: object) -> ContractAdmissionEvidence:
    """Return distinct semantic receipt identities unless a test overrides one."""
    values: dict[str, object] = {
        "contract_commit_sha": CONTRACT_SHA,
        "contract_asset_sha256": ARTIFACT_SHA256,
        "conformance_receipt_sha256": CONFORMANCE_SHA256,
        "bundle_manifest_sha256": BUNDLE_SHA256,
        "provenance_attestation_sha256": PROVENANCE_SHA256,
        "admission_state": "verified",
        "verified_at": datetime(2026, 9, 1, 6, 2, tzinfo=UTC),
        "compatibility_receipt_sha256": COMPATIBILITY_SHA256,
        "migration_receipt_sha256": MIGRATION_SHA256,
    }
    values.update(overrides)
    return ContractAdmissionEvidence(**values)


@pytest.mark.parametrize(
    ("field", "reused_digest"),
    [
        ("bundle_manifest_sha256", CONFORMANCE_SHA256),
        ("provenance_attestation_sha256", CONFORMANCE_SHA256),
        ("compatibility_receipt_sha256", CONFORMANCE_SHA256),
        ("migration_receipt_sha256", PROVENANCE_SHA256),
    ],
)
def test_semantically_distinct_receipts_cannot_reuse_one_artifact_identity(
    field: str, reused_digest: str
) -> None:
    """Do not let one evidence artifact satisfy multiple independent controls."""
    admission = _admission(**{field: reused_digest})

    with pytest.raises(ValueError, match="evidence receipt SHA-256 identities must be distinct"):
        evaluate_projection_readiness(_candidate(), _release(), admission)


def test_distinct_receipt_identities_validate_without_authorizing_handoff() -> None:
    """Keep well-formed independent receipts blocked until trusted control-plane integration."""
    decision = evaluate_projection_readiness(_candidate(), _release(), _admission())

    assert decision.ready is False
    assert decision.reason == "trusted_control_plane_evidence_not_available"
    assert decision.next_action == "integrate_released_context_graph_trust_contract"
