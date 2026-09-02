"""Contract tests for Orgmetra's Enterprise Architecture projection admission boundary."""

from __future__ import annotations

from datetime import UTC, datetime
from types import MappingProxyType

import pytest

from orgmetra_enterprise_architecture_projection import (
    ArchitectureProjectionCandidate,
    ContractAdmissionEvidence,
    ContractReleaseEvidence,
    ProjectionKind,
    ProjectionTruthStatus,
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


def _admission(**overrides: object) -> ContractAdmissionEvidence:
    """Return trusted-looking conformance, provenance, and lifecycle evidence."""
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


def test_unreleased_contract_blocks_projection_with_next_action() -> None:
    """Do not serialize or publish EA data before a reviewed immutable contract exists."""
    decision = evaluate_projection_readiness(_candidate(), None)

    assert decision.ready is False
    assert decision.truth_status is ProjectionTruthStatus.PROPOSED
    assert decision.reason == "context_graph_contract_release_not_admitted"
    assert decision.next_action == "install_approved_context_graph_contract_release"
    assert decision.contract_commit_sha is None
    assert decision.contract_asset_sha256 is None
    assert decision.contract_conformance_receipt_sha256 is None
    assert decision.contract_bundle_manifest_sha256 is None
    assert decision.contract_provenance_attestation_sha256 is None
    assert decision.contract_compatibility_receipt_sha256 is None
    assert decision.contract_migration_receipt_sha256 is None


def test_release_metadata_without_conformance_and_provenance_stays_blocked() -> None:
    """Do not treat a tag and artifact digest as semantic admission or provenance."""
    decision = evaluate_projection_readiness(_candidate(), _release())

    assert decision.ready is False
    assert decision.truth_status is ProjectionTruthStatus.PROPOSED
    assert decision.reason == "context_graph_contract_admission_not_verified"
    assert decision.next_action == "verify_released_context_graph_contract_admission"
    assert decision.contract_commit_sha == CONTRACT_SHA
    assert decision.contract_asset_sha256 == ARTIFACT_SHA256
    assert decision.contract_conformance_receipt_sha256 is None
    assert decision.contract_bundle_manifest_sha256 is None
    assert decision.contract_provenance_attestation_sha256 is None
    assert decision.contract_compatibility_receipt_sha256 is None
    assert decision.contract_migration_receipt_sha256 is None


def test_caller_constructed_complete_evidence_cannot_authorize_handoff() -> None:
    """Keep shape-complete caller evidence blocked until a repository-owned trust adapter exists."""
    decision = evaluate_projection_readiness(_candidate(), _release(), _admission())

    assert decision.ready is False
    assert decision.truth_status is ProjectionTruthStatus.PROPOSED
    assert decision.reason == "trusted_control_plane_evidence_not_available"
    assert decision.next_action == "integrate_released_context_graph_trust_contract"
    assert decision.contract_commit_sha == CONTRACT_SHA
    assert decision.contract_asset_sha256 == ARTIFACT_SHA256
    assert decision.contract_conformance_receipt_sha256 == CONFORMANCE_SHA256
    assert decision.contract_bundle_manifest_sha256 == BUNDLE_SHA256
    assert decision.contract_provenance_attestation_sha256 == PROVENANCE_SHA256
    assert decision.contract_compatibility_receipt_sha256 == COMPATIBILITY_SHA256
    assert decision.contract_migration_receipt_sha256 == MIGRATION_SHA256


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
        ("contract_commit_sha", "deadbeef", "40-character lowercase contract commit SHA"),
        ("contract_asset_sha256", "abc", "64-character lowercase contract asset SHA-256"),
        ("conformance_receipt_sha256", "abc", "64-character lowercase conformance receipt SHA-256"),
        ("bundle_manifest_sha256", "abc", "64-character lowercase bundle manifest SHA-256"),
        (
            "provenance_attestation_sha256",
            "abc",
            "64-character lowercase provenance attestation SHA-256",
        ),
        ("admission_state", "pending", "verified contract admission"),
        ("verified_at", datetime(2026, 9, 1), "timezone-aware admission verification time"),
    ],
)
def test_malformed_contract_admission_evidence_is_rejected(
    field: str, value: object, message: str
) -> None:
    """Reject incomplete or malformed semantic-admission and provenance evidence."""
    admission = _admission(**{field: value})

    with pytest.raises(ValueError, match=message):
        evaluate_projection_readiness(_candidate(), _release(), admission)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("contract_commit_sha", "e" * 40, "admission commit must match released commit"),
        ("contract_asset_sha256", "e" * 64, "admission asset must match released asset"),
    ],
)
def test_contract_admission_must_bind_the_exact_release(
    field: str, value: object, message: str
) -> None:
    """Reject valid-looking admission evidence for different released bytes."""
    admission = _admission(**{field: value})

    with pytest.raises(ValueError, match=message):
        evaluate_projection_readiness(_candidate(), _release(), admission)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("projection_key", "person:1234", "deployable architecture key"),
        ("projection_kind", "person", "supported architecture kind"),
        (
            "source_repository",
            "ContextualWisdomLab/enterprise-architecture-core",
            "Orgmetra source repository",
        ),
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
        ("owner_reference", "team:", "non-person architecture owner reference"),
        (
            "dependency_references",
            ("employment:abc",),
            "architecture-only dependency reference",
        ),
        (
            "dependency_references",
            ("service:",),
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


def test_open_ended_or_future_ended_effective_intervals_are_accepted() -> None:
    """Accept an ordered effective interval while keeping recorded time separate."""
    candidate = _candidate(effective_to=datetime(2026, 9, 2, tzinfo=UTC))

    assert candidate.effective_to == datetime(2026, 9, 2, tzinfo=UTC)


def test_candidate_collections_are_immutable_after_validation() -> None:
    """Prevent callers from mutating dependency evidence after admission checks."""
    candidate = _candidate(dependency_references=["service:keyverse", "service:naruon"])

    assert candidate.dependency_references == ("service:keyverse", "service:naruon")
    with pytest.raises(AttributeError):
        candidate.dependency_references.append("person:employee-1")  # type: ignore[attr-defined]


def test_unvalidated_candidate_object_cannot_bypass_constructor_checks() -> None:
    """Reject arbitrary objects even when contract-release evidence itself is valid."""
    with pytest.raises(TypeError, match="ArchitectureProjectionCandidate"):
        evaluate_projection_readiness(object(), _release())  # type: ignore[arg-type]


def test_unvalidated_release_object_cannot_bypass_release_evidence_type() -> None:
    """Reject duck-typed release objects before reading their caller-controlled fields."""
    with pytest.raises(TypeError, match="ContractReleaseEvidence"):
        evaluate_projection_readiness(_candidate(), object())  # type: ignore[arg-type]


def test_unvalidated_admission_object_cannot_bypass_admission_evidence_type() -> None:
    """Reject duck-typed semantic admission evidence at the trust boundary."""
    with pytest.raises(TypeError, match="ContractAdmissionEvidence"):
        evaluate_projection_readiness(_candidate(), _release(), object())  # type: ignore[arg-type]


def test_projection_decision_exposes_no_free_form_hr_payload() -> None:
    """Keep the adapter incapable of carrying person/employment/job decision payloads."""
    decision = evaluate_projection_readiness(_candidate(), _release(), _admission())

    assert not hasattr(decision, "payload")
    assert not hasattr(decision, "person")
    assert not hasattr(decision, "employment")
    assert not hasattr(decision, "job")
    assert MappingProxyType({}) == {}


def test_projection_kind_covers_declared_ea_decision_plane_scope() -> None:
    """Keep executable projection concepts aligned with the declared EA handoff contract."""
    required_kinds = {
        "application",
        "service",
        "api",
        "worker",
        "database",
        "runtime",
        "provider",
        "technology_version",
        "lifecycle",
        "risk",
        "ownership",
        "remediation",
        "transformation",
    }

    assert required_kinds <= {kind.value for kind in ProjectionKind}
