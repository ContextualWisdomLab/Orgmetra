"""Fail-closed admission boundary for Orgmetra Enterprise Architecture projections.

This package validates Orgmetra-owned architecture projection candidates and the
shape and internal consistency of external release, conformance, provenance,
compatibility, and migration evidence. Caller-created evidence is never enough
to authorize an Enterprise Architecture handoff: positive admission remains
closed until Orgmetra has a repository-owned adapter for the immutable trust
contract published by the Context Graph owner. The package does not serialize
the foreign contract, write Enterprise Architecture state, or transport
authoritative HR records.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
import json
import re
from typing import NamedTuple


_ORGMETRA_REPOSITORY = "ContextualWisdomLab/Orgmetra"
_CONTRACT_REPOSITORY = "ContextualWisdomLab/context-graph-contracts"
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_RELEASE_TAG_RE = re.compile(r"^v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)$")
_PROJECTION_KEY_RE = re.compile(r"^orgmetra\.[a-z0-9][a-z0-9._-]*$")
_OWNER_REFERENCE_RE = re.compile(r"^(?:team|organization|application):[a-z0-9][a-z0-9._/-]*$")
_DEPENDENCY_REFERENCE_RE = re.compile(
    r"^(?:application|service|interface|technology|provider|capability):[a-z0-9][a-z0-9._/-]*$"
)


class ProjectionKind(StrEnum):
    """Architecture concepts Orgmetra may describe without becoming their authority."""

    APPLICATION = "application"
    SERVICE = "service"
    API = "api"
    WORKER = "worker"
    DATABASE = "database"
    RUNTIME = "runtime"
    INTERFACE = "interface"
    TECHNOLOGY_COMPONENT = "technology_component"
    TECHNOLOGY_VERSION = "technology_version"
    PROVIDER = "provider"
    LIFECYCLE = "lifecycle"
    RISK = "risk"
    OWNERSHIP = "ownership"
    REMEDIATION = "remediation"
    CAPABILITY = "capability"
    INITIATIVE = "initiative"
    TRANSFORMATION = "transformation"
    DEPENDENCY = "dependency"


class ProjectionTruthStatus(StrEnum):
    """Truth status available before the Enterprise Architecture owner accepts data."""

    PROPOSED = "proposed"


@dataclass(frozen=True, slots=True)
class ArchitectureProjectionCandidate:
    """Minimal Orgmetra-owned evidence that may become an EA projection candidate."""

    projection_key: str
    projection_kind: ProjectionKind
    source_revision: str
    source_repository: str
    effective_from: datetime
    effective_to: datetime | None
    recorded_at: datetime
    owner_reference: str
    dependency_references: tuple[str, ...]

    def __post_init__(self) -> None:
        """Normalize immutable collections and reject HR facts or malformed evidence."""
        object.__setattr__(self, "dependency_references", tuple(self.dependency_references))
        _validate_projection_candidate(self)


class ContractReleaseEvidence(NamedTuple):
    """Release-shape evidence that still requires repository-owned trust verification."""

    repository: str
    release_tag: str
    commit_sha: str
    asset_sha256: str
    release_state: str
    verified_at: datetime


class ContractAdmissionEvidence(NamedTuple):
    """Admission-shape evidence that still requires repository-owned trust verification."""

    contract_commit_sha: str
    contract_asset_sha256: str
    conformance_receipt_sha256: str
    bundle_manifest_sha256: str
    provenance_attestation_sha256: str
    admission_state: str
    verified_at: datetime
    compatibility_receipt_sha256: str | None = None
    migration_receipt_sha256: str | None = None


class _CandidateEvidenceSnapshot(NamedTuple):
    """Immutable local snapshot of the exact candidate values evaluated for readiness."""

    projection_key: str
    projection_kind: ProjectionKind
    source_revision: str
    source_repository: str
    effective_from: datetime
    effective_to: datetime | None
    recorded_at: datetime
    owner_reference: str
    dependency_references: tuple[str, ...]


class ProjectionReadiness(NamedTuple):
    """Immutable decision describing whether a candidate may be handed to the EA owner."""

    ready: bool
    truth_status: ProjectionTruthStatus
    source_repository: str
    source_revision: str
    candidate_sha256: str
    reason: str
    next_action: str
    contract_commit_sha: str | None
    contract_asset_sha256: str | None
    contract_conformance_receipt_sha256: str | None
    contract_bundle_manifest_sha256: str | None
    contract_provenance_attestation_sha256: str | None
    contract_compatibility_receipt_sha256: str | None
    contract_migration_receipt_sha256: str | None


def _require_exact_text(value: object, field_name: str) -> None:
    """Reject text subclasses whose comparison behavior can contradict stored evidence."""
    if type(value) is not str:
        raise TypeError(f"{field_name} must be exact built-in text")


def _require_aware_time(
    value: datetime,
    field_name: str,
    naive_requirement: str | None = None,
) -> None:
    """Accept only immutable built-in temporal behavior at the cross-system trust boundary."""
    if type(value) is not datetime:
        raise TypeError(f"{field_name} must use exact built-in datetime and timezone")
    if value.utcoffset() is None:
        requirement = naive_requirement if naive_requirement is not None else field_name
        raise ValueError(f"{field_name} must be timezone-aware {requirement}")
    if type(value.tzinfo) is not timezone:
        raise TypeError(f"{field_name} must use exact built-in datetime and timezone")


def _validate_projection_candidate(
    candidate: ArchitectureProjectionCandidate | _CandidateEvidenceSnapshot,
) -> None:
    """Revalidate retained candidate values before any readiness decision is issued."""
    _require_exact_text(candidate.projection_key, "projection_key")
    if _PROJECTION_KEY_RE.fullmatch(candidate.projection_key) is None:
        raise ValueError("projection_key must be a deployable architecture key")
    if not isinstance(candidate.projection_kind, ProjectionKind):
        raise ValueError("projection_kind must be a supported architecture kind")
    _require_exact_text(candidate.source_repository, "source_repository")
    if candidate.source_repository != _ORGMETRA_REPOSITORY:
        raise ValueError("source_repository must be the Orgmetra source repository")
    _require_exact_text(candidate.source_revision, "source_revision")
    if _SHA_RE.fullmatch(candidate.source_revision) is None:
        raise ValueError("source_revision must be a 40-character lowercase source revision")
    _require_aware_time(candidate.effective_from, "effective_from")
    _require_aware_time(candidate.recorded_at, "recorded_at")
    if candidate.effective_to is not None:
        _require_aware_time(candidate.effective_to, "effective_to")
        if candidate.effective_to <= candidate.effective_from:
            raise ValueError("effective_to must be after effective_from")
    _require_exact_text(candidate.owner_reference, "owner_reference")
    if _OWNER_REFERENCE_RE.fullmatch(candidate.owner_reference) is None:
        raise ValueError("owner_reference must be a non-person architecture owner reference")
    if type(candidate.dependency_references) is not tuple:
        raise ValueError("dependency_references must remain an immutable tuple")
    for reference in candidate.dependency_references:
        _require_exact_text(reference, "dependency reference")
        if _DEPENDENCY_REFERENCE_RE.fullmatch(reference) is None:
            raise ValueError(
                "dependency_references must contain architecture-only dependency reference values"
            )


def _snapshot_projection_candidate(
    candidate: ArchitectureProjectionCandidate,
) -> _CandidateEvidenceSnapshot:
    """Detach evaluated candidate values from the caller-owned object before handoff evidence."""
    _validate_projection_candidate(candidate)
    snapshot = _CandidateEvidenceSnapshot(
        projection_key=candidate.projection_key,
        projection_kind=candidate.projection_kind,
        source_revision=candidate.source_revision,
        source_repository=candidate.source_repository,
        effective_from=candidate.effective_from,
        effective_to=candidate.effective_to,
        recorded_at=candidate.recorded_at,
        owner_reference=candidate.owner_reference,
        dependency_references=candidate.dependency_references,
    )
    _validate_projection_candidate(snapshot)
    return snapshot


def _candidate_sha256(candidate: _CandidateEvidenceSnapshot) -> str:
    """Hash the exact allowed architecture evidence so readiness cannot move between candidates."""
    payload = {
        "dependency_references": list(candidate.dependency_references),
        "effective_from": candidate.effective_from.isoformat(),
        "effective_to": candidate.effective_to.isoformat() if candidate.effective_to is not None else None,
        "owner_reference": candidate.owner_reference,
        "projection_key": candidate.projection_key,
        "projection_kind": candidate.projection_kind.value,
        "recorded_at": candidate.recorded_at.isoformat(),
        "source_repository": candidate.source_repository,
        "source_revision": candidate.source_revision,
    }
    canonical = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validate_contract_release(release: ContractReleaseEvidence) -> None:
    """Require immutable-looking evidence for the exact foreign contract authority."""
    _require_exact_text(release.repository, "repository")
    if release.repository != _CONTRACT_REPOSITORY:
        raise ValueError("unexpected contract repository")
    _require_exact_text(release.release_tag, "release_tag")
    if _RELEASE_TAG_RE.fullmatch(release.release_tag) is None:
        raise ValueError("release_tag must be a stable release tag")
    _require_exact_text(release.commit_sha, "commit_sha")
    if _SHA_RE.fullmatch(release.commit_sha) is None:
        raise ValueError("commit_sha must be a 40-character lowercase commit SHA")
    _require_exact_text(release.asset_sha256, "asset_sha256")
    if _SHA256_RE.fullmatch(release.asset_sha256) is None:
        raise ValueError("asset_sha256 must be a 64-character lowercase SHA-256")
    _require_exact_text(release.release_state, "release_state")
    if release.release_state != "published":
        raise ValueError("release_state must identify a published release")
    _require_aware_time(release.verified_at, "verified_at", "verification time")


def _validate_optional_receipt(
    value: str | None,
    field_name: str,
    receipt_name: str,
) -> None:
    """Validate an optional lifecycle receipt when a control plane supplies one."""
    if value is None:
        return
    _require_exact_text(value, field_name)
    if _SHA256_RE.fullmatch(value) is None:
        raise ValueError(
            f"{field_name} must be a 64-character lowercase {receipt_name} SHA-256"
        )


def _validate_contract_admission(
    admission: ContractAdmissionEvidence,
    release: ContractReleaseEvidence,
) -> None:
    """Bind semantic, bundle, provenance, and lifecycle evidence to released bytes."""
    _require_exact_text(admission.contract_commit_sha, "contract_commit_sha")
    if _SHA_RE.fullmatch(admission.contract_commit_sha) is None:
        raise ValueError("contract_commit_sha must be a 40-character lowercase contract commit SHA")
    _require_exact_text(admission.contract_asset_sha256, "contract_asset_sha256")
    if _SHA256_RE.fullmatch(admission.contract_asset_sha256) is None:
        raise ValueError("contract_asset_sha256 must be a 64-character lowercase contract asset SHA-256")
    _require_exact_text(admission.conformance_receipt_sha256, "conformance_receipt_sha256")
    if _SHA256_RE.fullmatch(admission.conformance_receipt_sha256) is None:
        raise ValueError(
            "conformance_receipt_sha256 must be a 64-character lowercase conformance receipt SHA-256"
        )
    _require_exact_text(admission.bundle_manifest_sha256, "bundle_manifest_sha256")
    if _SHA256_RE.fullmatch(admission.bundle_manifest_sha256) is None:
        raise ValueError(
            "bundle_manifest_sha256 must be a 64-character lowercase bundle manifest SHA-256"
        )
    _require_exact_text(
        admission.provenance_attestation_sha256,
        "provenance_attestation_sha256",
    )
    if _SHA256_RE.fullmatch(admission.provenance_attestation_sha256) is None:
        raise ValueError(
            "provenance_attestation_sha256 must be a 64-character lowercase provenance attestation SHA-256"
        )
    _require_exact_text(admission.admission_state, "admission_state")
    if admission.admission_state != "verified":
        raise ValueError("admission_state must identify verified contract admission")
    _require_aware_time(admission.verified_at, "verified_at", "admission verification time")
    if admission.verified_at < release.verified_at:
        raise ValueError("admission verification cannot predate release verification")
    if admission.contract_commit_sha != release.commit_sha:
        raise ValueError("admission commit must match released commit")
    if admission.contract_asset_sha256 != release.asset_sha256:
        raise ValueError("admission asset must match released asset")
    _validate_optional_receipt(
        admission.compatibility_receipt_sha256,
        "compatibility_receipt_sha256",
        "compatibility receipt",
    )
    _validate_optional_receipt(
        admission.migration_receipt_sha256,
        "migration_receipt_sha256",
        "migration receipt",
    )
    if (
        admission.compatibility_receipt_sha256 is not None
        and admission.migration_receipt_sha256 is not None
        and admission.compatibility_receipt_sha256
        == admission.migration_receipt_sha256
    ):
        raise ValueError(
            "compatibility and migration receipts must identify distinct lifecycle evidence"
        )
    receipt_digests = [
        admission.conformance_receipt_sha256,
        admission.bundle_manifest_sha256,
        admission.provenance_attestation_sha256,
    ]
    if admission.compatibility_receipt_sha256 is not None:
        receipt_digests.append(admission.compatibility_receipt_sha256)
    if admission.migration_receipt_sha256 is not None:
        receipt_digests.append(admission.migration_receipt_sha256)
    if len(receipt_digests) != len(set(receipt_digests)):
        raise ValueError("contract evidence receipt SHA-256 identities must be distinct")


def _blocked_readiness(
    candidate: _CandidateEvidenceSnapshot,
    candidate_sha256: str,
    reason: str,
    next_action: str,
    release: ContractReleaseEvidence | None = None,
    admission: ContractAdmissionEvidence | None = None,
) -> ProjectionReadiness:
    """Build one immutable fail-closed decision without dropping validated evidence."""
    return ProjectionReadiness(
        ready=False,
        truth_status=ProjectionTruthStatus.PROPOSED,
        source_repository=candidate.source_repository,
        source_revision=candidate.source_revision,
        candidate_sha256=candidate_sha256,
        reason=reason,
        next_action=next_action,
        contract_commit_sha=release.commit_sha if release is not None else None,
        contract_asset_sha256=release.asset_sha256 if release is not None else None,
        contract_conformance_receipt_sha256=(
            admission.conformance_receipt_sha256 if admission is not None else None
        ),
        contract_bundle_manifest_sha256=(
            admission.bundle_manifest_sha256 if admission is not None else None
        ),
        contract_provenance_attestation_sha256=(
            admission.provenance_attestation_sha256 if admission is not None else None
        ),
        contract_compatibility_receipt_sha256=(
            admission.compatibility_receipt_sha256 if admission is not None else None
        ),
        contract_migration_receipt_sha256=(
            admission.migration_receipt_sha256 if admission is not None else None
        ),
    )


def evaluate_projection_readiness(
    candidate: ArchitectureProjectionCandidate,
    contract_release: ContractReleaseEvidence | None,
    contract_admission: ContractAdmissionEvidence | None = None,
) -> ProjectionReadiness:
    """Validate caller evidence while keeping handoff closed until trusted owner integration."""
    if type(candidate) is not ArchitectureProjectionCandidate:
        raise TypeError("candidate must be an ArchitectureProjectionCandidate")
    candidate_snapshot = _snapshot_projection_candidate(candidate)
    candidate_sha256 = _candidate_sha256(candidate_snapshot)
    if contract_release is None:
        return _blocked_readiness(
            candidate_snapshot,
            candidate_sha256,
            reason="context_graph_contract_release_not_admitted",
            next_action="install_approved_context_graph_contract_release",
        )
    if type(contract_release) is not ContractReleaseEvidence:
        raise TypeError("contract_release must be ContractReleaseEvidence or None")
    _validate_contract_release(contract_release)
    if contract_admission is None:
        return _blocked_readiness(
            candidate_snapshot,
            candidate_sha256,
            reason="context_graph_contract_admission_not_verified",
            next_action="verify_released_context_graph_contract_admission",
            release=contract_release,
        )
    if type(contract_admission) is not ContractAdmissionEvidence:
        raise TypeError("contract_admission must be ContractAdmissionEvidence or None")
    _validate_contract_admission(contract_admission, contract_release)
    if (
        contract_admission.compatibility_receipt_sha256 is None
        or contract_admission.migration_receipt_sha256 is None
    ):
        return _blocked_readiness(
            candidate_snapshot,
            candidate_sha256,
            reason="context_graph_contract_lifecycle_evidence_not_verified",
            next_action="verify_context_graph_contract_compatibility_and_migration",
            release=contract_release,
            admission=contract_admission,
        )
    return _blocked_readiness(
        candidate_snapshot,
        candidate_sha256,
        reason="trusted_control_plane_evidence_not_available",
        next_action="integrate_released_context_graph_trust_contract",
        release=contract_release,
        admission=contract_admission,
    )
