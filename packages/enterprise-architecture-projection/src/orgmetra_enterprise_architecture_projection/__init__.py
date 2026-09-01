"""Fail-closed admission boundary for Orgmetra Enterprise Architecture projections.

This package validates Orgmetra-owned architecture projection candidates and the
release evidence required before they can be handed to the Enterprise
Architecture owner. It does not serialize the foreign context-graph contract,
write Enterprise Architecture state, or transport authoritative HR records.
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
        if _PROJECTION_KEY_RE.fullmatch(self.projection_key) is None:
            raise ValueError("projection_key must be a deployable architecture key")
        if not isinstance(self.projection_kind, ProjectionKind):
            raise ValueError("projection_kind must be a supported architecture kind")
        if self.source_repository != _ORGMETRA_REPOSITORY:
            raise ValueError("source_repository must be the Orgmetra source repository")
        if _SHA_RE.fullmatch(self.source_revision) is None:
            raise ValueError("source_revision must be a 40-character lowercase source revision")
        _require_aware_time(self.effective_from, "effective_from")
        _require_aware_time(self.recorded_at, "recorded_at")
        if self.effective_to is not None:
            _require_aware_time(self.effective_to, "effective_to")
            if self.effective_to <= self.effective_from:
                raise ValueError("effective_to must be after effective_from")
        if _OWNER_REFERENCE_RE.fullmatch(self.owner_reference) is None:
            raise ValueError("owner_reference must be a non-person architecture owner reference")
        dependencies = tuple(self.dependency_references)
        if any(
            _DEPENDENCY_REFERENCE_RE.fullmatch(reference) is None
            for reference in dependencies
        ):
            raise ValueError(
                "dependency_references must contain architecture-only dependency reference values"
            )
        object.__setattr__(self, "dependency_references", dependencies)


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
class ProjectionReadiness:
    """Decision describing whether a candidate may be handed to the EA owner."""

    ready: bool
    truth_status: ProjectionTruthStatus
    reason: str
    next_action: str
    contract_commit_sha: str | None
    contract_asset_sha256: str | None


def _require_aware_time(value: datetime, field_name: str) -> None:
    """Reject naive timestamps because projection evidence is compared across systems."""
    if value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware {field_name}")


def _validate_contract_release(release: ContractReleaseEvidence) -> None:
    """Require immutable-looking evidence for the exact foreign contract authority."""
    if release.repository != _CONTRACT_REPOSITORY:
        raise ValueError("unexpected contract repository")
    if _RELEASE_TAG_RE.fullmatch(release.release_tag) is None:
        raise ValueError("release_tag must be a stable release tag")
    if _SHA_RE.fullmatch(release.commit_sha) is None:
        raise ValueError("commit_sha must be a 40-character lowercase commit SHA")
    if _SHA256_RE.fullmatch(release.asset_sha256) is None:
        raise ValueError("asset_sha256 must be a 64-character lowercase SHA-256")
    if release.release_state != "published":
        raise ValueError("release_state must identify a published release")
    if release.verified_at.utcoffset() is None:
        raise ValueError("verified_at must be a timezone-aware verification time")


def evaluate_projection_readiness(
    candidate: ArchitectureProjectionCandidate,
    contract_release: ContractReleaseEvidence | None,
) -> ProjectionReadiness:
    """Return fail-closed readiness without conferring Enterprise Architecture truth."""
    if type(candidate) is not ArchitectureProjectionCandidate:
        raise TypeError("candidate must be an ArchitectureProjectionCandidate")
    if contract_release is None:
        return ProjectionReadiness(
            ready=False,
            truth_status=ProjectionTruthStatus.PROPOSED,
            reason="context_graph_contract_release_not_admitted",
            next_action="install_approved_context_graph_contract_release",
            contract_commit_sha=None,
            contract_asset_sha256=None,
        )
    if type(contract_release) is not ContractReleaseEvidence:
        raise TypeError("contract_release must be ContractReleaseEvidence or None")
    _validate_contract_release(contract_release)
    return ProjectionReadiness(
        ready=True,
        truth_status=ProjectionTruthStatus.PROPOSED,
        reason="projection_candidate_ready",
        next_action="submit_candidate_to_enterprise_architecture_owner",
        contract_commit_sha=contract_release.commit_sha,
        contract_asset_sha256=contract_release.asset_sha256,
    )
