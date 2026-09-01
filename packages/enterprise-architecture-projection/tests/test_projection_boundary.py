"""Contract tests for Orgmetra's Enterprise Architecture projection admission boundary."""

from __future__ import annotations

from datetime import UTC, datetime
from types import MappingProxyType

import pytest

from orgmetra_enterprise_architecture_projection import (
    ArchitectureProjectionCandidate,
    ContractReleaseEvidence,
    ProjectionKind,
    ProjectionTruthStatus,
    evaluate_projection_readiness,
)


ORGMETRA_SHA = "9e3e4847510e1e612b48474ba42b177b8ed824df"
CONTRACT_SHA = "99d230991b9d48fbf87489e0b375b7bbf09d8559"
ARTIFACT_SHA256 = "a" * 64


def _candidate(**overrides: object) -> ArchitectureProjectionCandidate:
    """Return a minimal deployable-architecture candidate with optional overrides."""
    values: dict[str, object] = {
        "projection_key": "orgmetra.people-api",
        "projection_kind": ProjectionKind.APPLICATION,
        "source_revision": ORGMETRA_SHA,
        "source_repository": "ContextualWisdomLab/Orgmetra",
        "effective_from": datetime(2026, 9, 1, tzinfo=UTC),
        "effective_to": None,
        "recorded_at": datetime(2026, 9, 1, 6, 0, tzinfo=UTC),
        "owner_reference": "team:orgmetra",
        "dependency_references": ("service:keyverse",),
    }
    values.update(overrides)
    return ArchitectureProjectionCandidate(**values)


def _release(**overrides: object) -> ContractReleaseEvidence:
    """Return immutable-looking context-graph release evidence with optional overrides."""
    values: dict[str, object] = {
        "repository": "ContextualWisdomLab/context-graph-contracts",
        "release_tag": "v1.0.0",
        "commit_sha": CONTRACT_SHA,
        "asset_sha256": ARTIFACT_SHA256,
        "release_state": "published",
        "verified_at": datetime(2026, 9, 1, 6, 1, tzinfo=UTC),
    }
    values.update(overrides)
    return ContractReleaseEvidence(**values)


def test_unreleased_contract_blocks_projection_with_next_action() -> None:
    """Do not serialize or publish EA data before a reviewed immutable contract exists."""
    decision = evaluate_projection_readiness(_candidate(), None)

    assert decision.ready is False
    assert decision.truth_status is ProjectionTruthStatus.PROPOSED
    assert decision.reason == "context_graph_contract_release_not_admitted"
    assert decision.next_action == "install_approved_context_graph_contract_release"
    assert decision.contract_commit_sha is None
    assert decision.contract_asset_sha256 is None


def test_published_contract_evidence_admits_only_a_candidate_not_ea_truth() -> None:
    """Admit a candidate after release pinning without granting EA authoritative status."""
    decision = evaluate_projection_readiness(_candidate(), _release())

    assert decision.ready is True
    assert decision.truth_status is ProjectionTruthStatus.PROPOSED
    assert decision.reason == "projection_candidate_ready"
    assert decision.next_action == "submit_candidate_to_enterprise_architecture_owner"
    assert decision.contract_commit_sha == CONTRACT_SHA
    assert decision.contract_asset_sha256 == ARTIFACT_SHA256


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("repository", "ContextualWisdomLab/Orgmetra", "unexpected contract repository"),
        ("release_tag", "main", "stable release tag"),
        ("commit_sha", "deadbeef", "40-character lowercase commit SHA"),
        ("asset_sha256", "abc", "64-character lowercase SHA-256"),
        ("release_state", "draft", "published release"),
        ("verified_at", datetime(2026, 9, 1), "timezone-aware verification time"),
    ],
)
def test_untrusted_contract_release_evidence_is_rejected(
    field: str, value: object, message: str
) -> None:
    """Reject mutable, unpublished, malformed, or foreign contract-release evidence."""
    release = _release(**{field: value})

    with pytest.raises(ValueError, match=message):
        evaluate_projection_readiness(_candidate(), release)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("projection_key", "person:1234", "deployable architecture key"),
        ("source_repository", "ContextualWisdomLab/enterprise-architecture-core", "Orgmetra source repository"),
        ("source_revision", "not-a-sha", "40-character lowercase source revision"),
        ("effective_from", datetime(2026, 9, 1), "timezone-aware effective_from"),
        (
            "recorded_at",
            datetime(2026, 9, 1),
            "timezone-aware recorded_at",
        ),
        (
            "effective_to",
            datetime(2026, 8, 31, tzinfo=UTC),
            "effective_to must be after effective_from",
        ),
        ("owner_reference", "person:employee-123", "non-person architecture owner reference"),
        (
            "dependency_references",
            ("employment:abc",),
            "architecture-only dependency reference",
        ),
    ],
)
def test_hr_record_or_invalid_temporal_data_cannot_cross_into_ea_projection(
    field: str, value: object, message: str
) -> None:
    """Keep authoritative HR facts and malformed bitemporal evidence out of EA."""
    with pytest.raises(ValueError, match=message):
        _candidate(**{field: value})


def test_candidate_collections_are_immutable_after_validation() -> None:
    """Prevent callers from mutating dependency evidence after admission checks."""
    candidate = _candidate(dependency_references=["service:keyverse", "service:naruon"])

    assert candidate.dependency_references == ("service:keyverse", "service:naruon")
    with pytest.raises(AttributeError):
        candidate.dependency_references.append("person:employee-1")  # type: ignore[attr-defined]


def test_projection_decision_exposes_no_free_form_hr_payload() -> None:
    """Keep the adapter incapable of carrying person/employment/job decision payloads."""
    decision = evaluate_projection_readiness(_candidate(), _release())

    assert not hasattr(decision, "payload")
    assert not hasattr(decision, "person")
    assert not hasattr(decision, "employment")
    assert not hasattr(decision, "job")
    assert MappingProxyType({}) == {}
