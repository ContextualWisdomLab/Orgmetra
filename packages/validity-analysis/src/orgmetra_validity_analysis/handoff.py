"""Governed handoff evidence for criterion-related selection validation.

This package does not execute statistics, read another service's database, or make an
employment decision. It binds authoritative Orgmetra evidence to one reviewed,
immutable fast-mlsirm revision so an approved offline worker can perform numerical
analysis without silently changing the study definition.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from uuid import UUID

_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_REVISION_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_REFERENCE_PATTERN = re.compile(
    r"^[a-z][a-z0-9_]{1,31}:[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9])?$"
)
_PURPOSE_CODE = "selection_validity_analysis"
_REASON_CODE = "criterion_related_validation"
_VALIDATION_STRATEGY = "criterion_related"
_KERNEL_REPOSITORY = "ContextualWisdomLab/fast-mlsirm"
REVIEWED_FAST_MLSIRM_REVISION = "04d0bc21a2a20693bcf16108cd76d394fe844d23"
_KERNEL_BOUNDARY = "read_only_pinned_revision"
_EXECUTION_STATE = "not_executed"
_RESULT_AUTHORITY = "scientific_evidence_only"
_REQUIRED_RESULT_EVIDENCE = (
    "effect_estimate",
    "uncertainty_interval",
    "sample_size",
    "missingness_summary",
    "convergence_diagnostics",
)
_NEXT_ACTION = (
    "Within tenant_record_id, re-resolve the validation study, Job, predictor, criterion, "
    "population, decision-policy, analysis-plan, requester, and reviewer references; prove "
    "requester and reviewer resolve to distinct authoritative actor identities; prove the "
    "predictor/criterion/population cases belong to the exact study and Job; then let an "
    "approved offline validation worker invoke only the pinned fast-mlsirm revision. Preserve "
    "the resulting model/provenance diagnostics as draft scientific evidence for an "
    "accountable human reviewer; never convert the result directly into an employment decision."
)


def _validate_operational_uuid(value: str, field_name: str) -> None:
    """Require canonical non-sentinel UUID text owned by authoritative Orgmetra."""
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(f"{field_name} must be canonical UUID text") from exc
    if str(parsed) != value or parsed.int in (0, (1 << 128) - 1):
        raise ValueError(f"{field_name} must be a canonical operational UUID")


def _validate_reference(value: str, prefix: str, field_name: str) -> None:
    """Require the expected namespace plus a canonical opaque UUIDv4 suffix."""
    error_message = f"{field_name} must be an opaque {prefix}: UUIDv4 reference"
    if (
        not isinstance(value, str)
        or len(value) > 160
        or not _REFERENCE_PATTERN.fullmatch(value)
        or not value.startswith(f"{prefix}:")
    ):
        raise ValueError(error_message)
    suffix = value.split(":", 1)[1]
    try:
        parsed = UUID(suffix)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(error_message) from exc
    if str(parsed) != suffix or parsed.version != 4 or parsed.int in (0, (1 << 128) - 1):
        raise ValueError(error_message)


def _validate_digest(value: str, field_name: str) -> None:
    """Require lowercase SHA-256 hexadecimal evidence."""
    if not isinstance(value, str) or not _DIGEST_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be lowercase SHA-256 hex")


def _validate_code(value: str, field_name: str) -> None:
    """Require bounded descriptive lower snake_case governance codes."""
    if not isinstance(value, str) or len(value) > 64 or not _CODE_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be bounded two-or-more-word lower snake_case")


def _validate_kernel_revision(value: str) -> None:
    """Require the exact externally reviewed immutable fast-mlsirm revision."""
    if not isinstance(value, str) or not _REVISION_PATTERN.fullmatch(value):
        raise ValueError("fast_mlsirm_revision must be lowercase 40-character Git commit hex")
    if value != REVIEWED_FAST_MLSIRM_REVISION:
        raise ValueError("fast_mlsirm_revision must equal the reviewed immutable revision")


def _canonical_timestamp(value: datetime, field_name: str) -> str:
    """Render an exact built-in aware instant with field-correct diagnostics."""
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True, repr=False)
class ValidationAnalysisHandoff:
    """Immutable evidence for one not-yet-executed criterion-related validity analysis."""

    tenant_record_id: str
    handoff_reference: str
    validation_study_reference: str
    job_profile_reference: str
    predictor_snapshot_reference: str
    predictor_snapshot_digest: str
    criterion_snapshot_reference: str
    criterion_snapshot_digest: str
    population_snapshot_reference: str
    population_snapshot_digest: str
    decision_policy_reference: str
    decision_policy_digest: str
    analysis_plan_reference: str
    analysis_plan_digest: str
    actor_reference: str
    reviewer_reference: str
    fast_mlsirm_revision: str
    requested_at: datetime
    purpose_code: str = _PURPOSE_CODE
    reason_code: str = _REASON_CODE
    evidence_version: int = 1
    validation_strategy: str = _VALIDATION_STRATEGY
    kernel_repository: str = _KERNEL_REPOSITORY
    kernel_boundary: str = _KERNEL_BOUNDARY
    execution_state: str = _EXECUTION_STATE
    contains_raw_person_level_values: bool = False
    human_review_required: bool = True
    result_authority: str = _RESULT_AUTHORITY
    required_result_evidence: tuple[str, ...] = _REQUIRED_RESULT_EVIDENCE
    next_action: str = _NEXT_ACTION

    def __post_init__(self) -> None:
        """Fail closed when direct construction drifts from the governed handoff."""
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        for value, prefix, field_name in (
            (self.handoff_reference, "validation_analysis_handoff", "handoff_reference"),
            (self.validation_study_reference, "validation_study", "validation_study_reference"),
            (self.job_profile_reference, "job_profile", "job_profile_reference"),
            (self.predictor_snapshot_reference, "predictor_snapshot", "predictor_snapshot_reference"),
            (self.criterion_snapshot_reference, "criterion_snapshot", "criterion_snapshot_reference"),
            (self.population_snapshot_reference, "study_population_snapshot", "population_snapshot_reference"),
            (self.decision_policy_reference, "decision_policy", "decision_policy_reference"),
            (self.analysis_plan_reference, "validation_analysis_plan", "analysis_plan_reference"),
            (self.actor_reference, "actor", "actor_reference"),
            (self.reviewer_reference, "actor", "reviewer_reference"),
        ):
            _validate_reference(value, prefix, field_name)
        for value, field_name in (
            (self.predictor_snapshot_digest, "predictor_snapshot_digest"),
            (self.criterion_snapshot_digest, "criterion_snapshot_digest"),
            (self.population_snapshot_digest, "population_snapshot_digest"),
            (self.decision_policy_digest, "decision_policy_digest"),
            (self.analysis_plan_digest, "analysis_plan_digest"),
        ):
            _validate_digest(value, field_name)
        if self.actor_reference == self.reviewer_reference:
            raise ValueError("reviewer_reference must identify a different accountable actor")
        _validate_kernel_revision(self.fast_mlsirm_revision)
        _canonical_timestamp(self.requested_at, "requested_at")
        _validate_code(self.purpose_code, "purpose_code")
        if self.purpose_code != _PURPOSE_CODE:
            raise ValueError("purpose_code must remain selection_validity_analysis")
        _validate_code(self.reason_code, "reason_code")
        if self.reason_code != _REASON_CODE:
            raise ValueError("reason_code must remain criterion_related_validation")
        if type(self.evidence_version) is not int or not 1 <= self.evidence_version <= 2_147_483_647:
            raise ValueError("evidence_version must be an integer from 1 through 2147483647")
        if self.validation_strategy != _VALIDATION_STRATEGY:
            raise ValueError("validation_strategy must remain criterion_related")
        if self.kernel_repository != _KERNEL_REPOSITORY:
            raise ValueError("kernel_repository must remain ContextualWisdomLab/fast-mlsirm")
        if self.kernel_boundary != _KERNEL_BOUNDARY:
            raise ValueError("kernel_boundary must remain read_only_pinned_revision")
        if self.execution_state != _EXECUTION_STATE:
            raise ValueError("execution_state must remain not_executed")
        if self.contains_raw_person_level_values is not False:
            raise ValueError("handoff must not contain raw person-level values")
        if self.human_review_required is not True:
            raise ValueError("human review is mandatory for selection-validity interpretation")
        if self.result_authority != _RESULT_AUTHORITY:
            raise ValueError("result_authority must remain scientific_evidence_only")
        if self.required_result_evidence != _REQUIRED_RESULT_EVIDENCE:
            raise ValueError("required_result_evidence must remain the reviewed evidence set")
        if self.next_action != _NEXT_ACTION:
            raise ValueError("next_action must remain the governed validation instruction")

    def __repr__(self) -> str:
        """Return a fully redacted representation suitable for routine logs."""
        return "ValidationAnalysisHandoff(<redacted>)"

    def canonical_json(self) -> str:
        """Return deterministic canonical JSON for audit and result correlation."""
        payload = {
            "actor_reference": self.actor_reference,
            "analysis_plan_digest": self.analysis_plan_digest,
            "analysis_plan_reference": self.analysis_plan_reference,
            "contains_raw_person_level_values": self.contains_raw_person_level_values,
            "criterion_snapshot_digest": self.criterion_snapshot_digest,
            "criterion_snapshot_reference": self.criterion_snapshot_reference,
            "decision_policy_digest": self.decision_policy_digest,
            "decision_policy_reference": self.decision_policy_reference,
            "evidence_version": self.evidence_version,
            "execution_state": self.execution_state,
            "fast_mlsirm_revision": self.fast_mlsirm_revision,
            "handoff_reference": self.handoff_reference,
            "human_review_required": self.human_review_required,
            "job_profile_reference": self.job_profile_reference,
            "kernel_boundary": self.kernel_boundary,
            "kernel_repository": self.kernel_repository,
            "next_action": self.next_action,
            "population_snapshot_digest": self.population_snapshot_digest,
            "population_snapshot_reference": self.population_snapshot_reference,
            "predictor_snapshot_digest": self.predictor_snapshot_digest,
            "predictor_snapshot_reference": self.predictor_snapshot_reference,
            "purpose_code": self.purpose_code,
            "reason_code": self.reason_code,
            "requested_at": _canonical_timestamp(self.requested_at, "requested_at"),
            "required_result_evidence": list(self.required_result_evidence),
            "result_authority": self.result_authority,
            "reviewer_reference": self.reviewer_reference,
            "tenant_record_id": self.tenant_record_id,
            "validation_strategy": self.validation_strategy,
            "validation_study_reference": self.validation_study_reference,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact canonical UTF-8 handoff."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


def build_validation_analysis_handoff(
    *,
    tenant_record_id: str,
    handoff_reference: str,
    validation_study_reference: str,
    job_profile_reference: str,
    predictor_snapshot_reference: str,
    predictor_snapshot_digest: str,
    criterion_snapshot_reference: str,
    criterion_snapshot_digest: str,
    population_snapshot_reference: str,
    population_snapshot_digest: str,
    decision_policy_reference: str,
    decision_policy_digest: str,
    analysis_plan_reference: str,
    analysis_plan_digest: str,
    actor_reference: str,
    reviewer_reference: str,
    fast_mlsirm_revision: str,
    requested_at: datetime,
) -> ValidationAnalysisHandoff:
    """Build a governed, non-executing selection-validity analysis handoff."""
    return ValidationAnalysisHandoff(
        tenant_record_id=tenant_record_id,
        handoff_reference=handoff_reference,
        validation_study_reference=validation_study_reference,
        job_profile_reference=job_profile_reference,
        predictor_snapshot_reference=predictor_snapshot_reference,
        predictor_snapshot_digest=predictor_snapshot_digest,
        criterion_snapshot_reference=criterion_snapshot_reference,
        criterion_snapshot_digest=criterion_snapshot_digest,
        population_snapshot_reference=population_snapshot_reference,
        population_snapshot_digest=population_snapshot_digest,
        decision_policy_reference=decision_policy_reference,
        decision_policy_digest=decision_policy_digest,
        analysis_plan_reference=analysis_plan_reference,
        analysis_plan_digest=analysis_plan_digest,
        actor_reference=actor_reference,
        reviewer_reference=reviewer_reference,
        fast_mlsirm_revision=fast_mlsirm_revision,
        requested_at=requested_at,
    )
