"""Fail-closed admission boundary for Orgmetra Enterprise Architecture projections.

This package validates Orgmetra-owned architecture projection candidates and the
release, semantic-conformance, bundle-identity, and provenance evidence required
before they can be handed to the Enterprise Architecture owner. It does not
serialize the foreign context-graph contract, write Enterprise Architecture
state, or transport authoritative HR records.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
import re


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
    INTERFACE = "interface"
    TECHNOLOGY_COMPONENT = "technology_component"
    TECHNOLOGY_VERSION = "technology_version"
    PROVIDER = "provider"
    LIFECYCLE = "lifecycle"
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


@dataclass(frozen=True, slots=True)
class ContractReleaseEvidence:
    """Trusted-control-plane observation of a published context-graph release."""

    repository: str
    release_tag: str
    commit_sha: str
    asset_sha256: str
    release_state: str
    verified_at: datetime


@dataclass(frozen=True, slots=True)
class ContractAdmissionEvidence:
    """Trusted evidence that exact released contract bytes passed semantic admission."""

    contract_commit_sha: str
    contract_asset_sha256: str
    conformance_receipt_sha256: str
    bundle_manifest_sha256: str
    provenance_attestation_sha256: str
    admission_state: str
    verified_at: datetime


@dataclass(frozen=True, slots=True)
class ProjectionReadiness:
    """Decision describing whether a candidate may be handed to the EA owner."""

    ready: bool
    truth_status: ProjectionTruthStatus
    reason: str
    next_action: str
    contract_commit_sha: str | None
    contract_asset_sha256: str | None
    contract_conformance_receipt_sha256: str | None
    contract_bundle_manifest_sha256: str | None
    contract_provenance_attestation_sha256: str | None


def _require_exact_text(value: object, field_name: str) -> None:
    """Reject text subclasses whose comparison behavior can contradict stored evidence."""
    if type(value) is not str:
        raise TypeError(f"{field_name} must be exact built-in text")


def _require_aware_time(value: datetime, field_name: str) -> None:
    """Reject naive timestamps because projection evidence is compared across systems."""
    if value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware {field_name}")


def _validate_projection_candidate(candidate: ArchitectureProjectionCandidate) -> None:
    """Revalidate the exact retained candidate before any readiness decision is issued."""
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
    if release.verified_at.utcoffset() is None:
        raise ValueError("verified_at must be a timezone-aware verification time")


def _validate_contract_admission(
    admission: ContractAdmissionEvidence,
    release: ContractReleaseEvidence,
) -> None:
    """Bind semantic, bundle, and provenance evidence to the exact released bytes."""
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
    if admission.verified_at.utcoffset() is None:
        raise ValueError("verified_at must be a timezone-aware admission verification time")
    if admission.contract_commit_sha != release.commit_sha:
        raise ValueError("admission commit must match released commit")
    if admission.contract_asset_sha256 != release.asset_sha256:
        raise ValueError("admission asset must match released asset")


def evaluate_projection_readiness(
    candidate: ArchitectureProjectionCandidate,
    contract_release: ContractReleaseEvidence | None,
    contract_admission: ContractAdmissionEvidence | None = None,
) -> ProjectionReadiness:
    """Return fail-closed readiness without conferring Enterprise Architecture truth."""
    if type(candidate) is not ArchitectureProjectionCandidate:
        raise TypeError("candidate must be an ArchitectureProjectionCandidate")
    _validate_projection_candidate(candidate)
    if contract_release is None:
        return ProjectionReadiness(
            ready=False,
            truth_status=ProjectionTruthStatus.PROPOSED,
            reason="context_graph_contract_release_not_admitted",
            next_action="install_approved_context_graph_contract_release",
            contract_commit_sha=None,
            contract_asset_sha256=None,
            contract_conformance_receipt_sha256=None,
            contract_bundle_manifest_sha256=None,
            contract_provenance_attestation_sha256=None,
        )
    if type(contract_release) is not ContractReleaseEvidence:
        raise TypeError("contract_release must be ContractReleaseEvidence or None")
    _validate_contract_release(contract_release)
    if contract_admission is None:
        return ProjectionReadiness(
            ready=False,
            truth_status=ProjectionTruthStatus.PROPOSED,
            reason="context_graph_contract_admission_not_verified",
            next_action="verify_released_context_graph_contract_admission",
            contract_commit_sha=contract_release.commit_sha,
            contract_asset_sha256=contract_release.asset_sha256,
            contract_conformance_receipt_sha256=None,
            contract_bundle_manifest_sha256=None,
            contract_provenance_attestation_sha256=None,
        )
    if type(contract_admission) is not ContractAdmissionEvidence:
        raise TypeError("contract_admission must be ContractAdmissionEvidence or None")
    _validate_contract_admission(contract_admission, contract_release)
    return ProjectionReadiness(
        ready=True,
        truth_status=ProjectionTruthStatus.PROPOSED,
        reason="projection_candidate_ready",
        next_action="submit_candidate_to_enterprise_architecture_owner",
        contract_commit_sha=contract_release.commit_sha,
        contract_asset_sha256=contract_release.asset_sha256,
        contract_conformance_receipt_sha256=contract_admission.conformance_receipt_sha256,
        contract_bundle_manifest_sha256=contract_admission.bundle_manifest_sha256,
        contract_provenance_attestation_sha256=contract_admission.provenance_attestation_sha256,
    )
