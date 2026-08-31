"""Governed adapter contracts for real pinned fast-mlsirm recovery evidence."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from math import isfinite
from numbers import Real
import json
import re
from uuid import UUID

from .handoff import REVIEWED_FAST_MLSIRM_REVISION

_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_REFERENCE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,63}:[0-9a-f-]{36}$")
_DESIGN_CODES = frozenset(
    {"cross_sectional", "nested_multilevel", "multiple_membership", "longitudinal"}
)
_RUNNABLE_DESIGNS = frozenset({"cross_sectional", "nested_multilevel"})
_RECOVERY_FIELDS = frozenset(
    {"parameter_rmse_mean", "latent_rmse", "distance_rmse", "gamma_abs_error"}
)
_WORKER_FIELDS = frozenset(
    {
        "model",
        "backend",
        "rust_device",
        "status",
        "n_iter",
        "objective",
        "n_persons",
        "n_items",
        "n_clusters",
        "recovery_summary",
    }
)


class UnsupportedExecutionDesign(ValueError):
    """Indicate that a valid design contract has no reviewed estimator yet."""


def _validate_fixed_text(value: object, expected: str, field_name: str) -> None:
    """Require exact built-in text before fixed-value comparisons or serialization."""
    if type(value) is not str or value != expected:
        raise ValueError(f"{field_name} must remain {expected}")


def _validate_reference(value: object, prefix: str, field_name: str) -> None:
    """Require an opaque UUID-shaped reference in the expected namespace."""
    if (
        type(value) is not str
        or not value.startswith(f"{prefix}:")
        or _REFERENCE_PATTERN.fullmatch(value) is None
    ):
        raise ValueError(f"{field_name} must be an opaque {prefix} reference")
    try:
        parsed = UUID(value.split(":", 1)[1])
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an opaque {prefix} reference") from exc
    if str(parsed) != value.split(":", 1)[1] or parsed.version != 4:
        raise ValueError(f"{field_name} must be an opaque {prefix} UUIDv4 reference")


def _validate_digest(value: object, field_name: str) -> None:
    """Require a lowercase SHA-256 digest without carrying the source values."""
    if type(value) is not str or _DIGEST_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be lowercase SHA-256 hex")


def _validate_positive_integer(value: object, field_name: str) -> None:
    """Require a positive integer and reject booleans as integers."""
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")


def _validate_nonnegative_integer(value: object, field_name: str) -> None:
    """Require a non-negative integer and reject booleans as integers."""
    if type(value) is not int or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")


def _finite_number(value: object, field_name: str) -> float:
    """Return one finite real number and reject booleans or non-numeric text."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{field_name} must be a finite number")
    number = float(value)
    if not isfinite(number):
        raise ValueError(f"{field_name} must be a finite number")
    return number


def _finite_nonnegative_number(value: object, field_name: str) -> float:
    """Return one finite non-negative real number."""
    number = _finite_number(value, field_name)
    if number < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return number


def _freeze_timestamp(value: object, field_name: str) -> datetime:
    """Detach caller-controlled timezone behavior and store one immutable UTC instant."""
    if type(value) is not datetime or value.tzinfo is None:
        raise ValueError(f"{field_name} must be an exact timezone-aware datetime")
    try:
        offset = value.utcoffset()
    except Exception as exc:  # noqa: BLE001 - normalize provider behavior at trust boundary.
        raise ValueError(f"{field_name} must be an exact timezone-aware datetime") from exc
    if type(offset) is not timedelta:
        raise ValueError(f"{field_name} must be an exact timezone-aware datetime")
    try:
        return (value.replace(tzinfo=None) - offset).replace(tzinfo=timezone.utc)
    except OverflowError as exc:
        raise ValueError(f"{field_name} must be an exact timezone-aware datetime") from exc


def _canonical_timestamp(value: object, field_name: str) -> str:
    """Render only a previously detached built-in UTC instant as RFC 3339 text."""
    if type(value) is not datetime or value.tzinfo is not timezone.utc:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True, repr=False)
class RustExecutionRequest:
    """Bind one non-person-level execution request to a reviewed Rust kernel."""

    execution_reference: str
    handoff_digest: str
    dataset_digest: str
    fast_mlsirm_revision: str
    design_code: str
    sample_size: int
    item_count: int
    seed: int
    cluster_count: int | None = None
    occasion_count: int = 1
    maximum_memberships: int = 1
    worker_count: int = 1
    backend: str = "rust"
    rust_device: str = "cpu"

    def __post_init__(self) -> None:
        """Fail closed on malformed identity, design, or execution metadata."""
        _validate_reference(
            self.execution_reference, "validity_execution", "execution_reference"
        )
        _validate_digest(self.handoff_digest, "handoff_digest")
        _validate_digest(self.dataset_digest, "dataset_digest")
        _validate_fixed_text(
            self.fast_mlsirm_revision,
            REVIEWED_FAST_MLSIRM_REVISION,
            "fast_mlsirm_revision",
        )
        if type(self.design_code) is not str:
            raise ValueError("design_code must be exact built-in text")
        if self.design_code not in _DESIGN_CODES:
            raise ValueError("design_code is not a governed execution design")
        _validate_fixed_text(self.backend, "rust", "backend")
        if type(self.rust_device) is not str or self.rust_device not in {"cpu", "gpu"}:
            raise ValueError("rust_device must be cpu or gpu")
        _validate_positive_integer(self.sample_size, "sample_size")
        _validate_positive_integer(self.item_count, "item_count")
        _validate_nonnegative_integer(self.seed, "seed")
        _validate_positive_integer(self.occasion_count, "occasion_count")
        _validate_positive_integer(self.maximum_memberships, "maximum_memberships")
        _validate_positive_integer(self.worker_count, "worker_count")
        if self.design_code == "nested_multilevel":
            if self.cluster_count is None or type(self.cluster_count) is not int or self.cluster_count < 2:
                raise ValueError("nested_multilevel requires cluster_count >= 2")
            if self.occasion_count != 1:
                raise ValueError("nested_multilevel requires occasion_count == 1")
            if self.maximum_memberships != 1:
                raise ValueError("nested_multilevel requires maximum_memberships == 1")
        elif self.design_code == "cross_sectional":
            if self.cluster_count is not None:
                raise ValueError("cross_sectional cannot carry cluster_count")
            if self.occasion_count != 1:
                raise ValueError("cross_sectional requires occasion_count == 1")
            if self.maximum_memberships != 1:
                raise ValueError("cross_sectional requires maximum_memberships == 1")
        elif self.design_code == "multiple_membership":
            if self.cluster_count is not None:
                raise ValueError("multiple_membership cannot carry cluster_count")
            if self.maximum_memberships < 2:
                raise ValueError("multiple_membership requires maximum_memberships >= 2")
        elif self.occasion_count < 2:
            raise ValueError("longitudinal requires occasion_count >= 2")

    @property
    def runnable(self) -> bool:
        """Return whether this design has a reviewed numerical execution path."""
        return self.design_code in _RUNNABLE_DESIGNS

    def require_runnable(self) -> None:
        """Raise when a valid contract has no reviewed estimator implementation."""
        if not self.runnable:
            raise UnsupportedExecutionDesign(
                f"{self.design_code} is contract-only; no reviewed estimator is available"
            )

    def __repr__(self) -> str:
        """Return a redacted representation suitable for routine logs."""
        return "RustExecutionRequest(<redacted>)"

    def canonical_json(self) -> str:
        """Return deterministic request metadata without raw observations."""
        payload = {
            "backend": self.backend,
            "cluster_count": self.cluster_count,
            "dataset_digest": self.dataset_digest,
            "design_code": self.design_code,
            "execution_reference": self.execution_reference,
            "fast_mlsirm_revision": self.fast_mlsirm_revision,
            "handoff_digest": self.handoff_digest,
            "item_count": self.item_count,
            "maximum_memberships": self.maximum_memberships,
            "occasion_count": self.occasion_count,
            "runnable": self.runnable,
            "rust_device": self.rust_device,
            "sample_size": self.sample_size,
            "seed": self.seed,
            "worker_count": self.worker_count,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact canonical request bytes."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True, repr=False)
class RustRecoveryEvidence:
    """Store aggregate simulation-recovery evidence without promoting validity."""

    evidence_reference: str
    request_digest: str
    fast_mlsirm_revision: str
    design_code: str
    backend: str
    rust_device: str
    model_code: str
    sample_size: int
    item_count: int
    cluster_count: int | None
    seed: int
    convergence_status: str
    iterations: int
    objective_value: Real
    parameter_rmse_mean: Real
    latent_rmse: Real
    distance_rmse: Real
    gamma_abs_error: Real
    completed_at: datetime
    result_authority: str = "scientific_evidence_only"
    execution_state: str = "completed"
    contains_raw_person_level_values: bool = False
    human_review_required: bool = True

    def __post_init__(self) -> None:
        """Reject unlinked, non-finite, or decision-like recovery evidence."""
        _validate_reference(
            self.evidence_reference,
            "validity_recovery_evidence",
            "evidence_reference",
        )
        _validate_digest(self.request_digest, "request_digest")
        _validate_fixed_text(
            self.fast_mlsirm_revision,
            REVIEWED_FAST_MLSIRM_REVISION,
            "fast_mlsirm_revision",
        )
        if type(self.design_code) is not str:
            raise ValueError("design_code must be exact built-in text")
        if self.design_code not in _RUNNABLE_DESIGNS:
            raise ValueError("recovery evidence requires a runnable design")
        _validate_fixed_text(self.backend, "rust", "backend")
        if type(self.rust_device) is not str or self.rust_device not in {"cpu", "gpu"}:
            raise ValueError("rust_device must be cpu or gpu")
        _validate_fixed_text(self.model_code, "mlsirm_recovery", "model_code")
        _validate_positive_integer(self.sample_size, "sample_size")
        _validate_positive_integer(self.item_count, "item_count")
        _validate_nonnegative_integer(self.seed, "seed")
        if self.design_code == "nested_multilevel":
            if self.cluster_count is None or type(self.cluster_count) is not int or self.cluster_count < 2:
                raise ValueError("nested_multilevel recovery evidence requires cluster_count >= 2")
            if self.cluster_count > self.sample_size:
                raise ValueError("nested_multilevel recovery evidence cluster_count cannot exceed sample_size")
        elif self.cluster_count is not None:
            raise ValueError("cross_sectional recovery evidence cannot carry cluster_count")
        if type(self.convergence_status) is not str or self.convergence_status not in {
            "converged",
            "max_iter_reached",
        }:
            raise ValueError("convergence_status is not a governed worker state")
        _validate_positive_integer(self.iterations, "iterations")
        object.__setattr__(
            self,
            "objective_value",
            _finite_number(self.objective_value, "objective_value"),
        )
        for field_name in (
            "parameter_rmse_mean",
            "latent_rmse",
            "distance_rmse",
            "gamma_abs_error",
        ):
            object.__setattr__(
                self,
                field_name,
                _finite_nonnegative_number(getattr(self, field_name), field_name),
            )
        object.__setattr__(self, "completed_at", _freeze_timestamp(self.completed_at, "completed_at"))
        _validate_fixed_text(
            self.result_authority,
            "scientific_evidence_only",
            "result_authority",
        )
        _validate_fixed_text(self.execution_state, "completed", "execution_state")
        if self.contains_raw_person_level_values is not False:
            raise ValueError("recovery evidence must not contain raw person-level values")
        if self.human_review_required is not True:
            raise ValueError("human review is mandatory for scientific evidence")

    def __repr__(self) -> str:
        """Return a redacted representation suitable for routine logs."""
        return "RustRecoveryEvidence(<redacted>)"

    def canonical_json(self) -> str:
        """Return deterministic aggregate recovery evidence for audit correlation."""
        payload = {
            "backend": self.backend,
            "cluster_count": self.cluster_count,
            "completed_at": _canonical_timestamp(self.completed_at, "completed_at"),
            "contains_raw_person_level_values": self.contains_raw_person_level_values,
            "convergence_status": self.convergence_status,
            "design_code": self.design_code,
            "distance_rmse": float(self.distance_rmse),
            "evidence_reference": self.evidence_reference,
            "execution_state": self.execution_state,
            "fast_mlsirm_revision": self.fast_mlsirm_revision,
            "gamma_abs_error": float(self.gamma_abs_error),
            "human_review_required": self.human_review_required,
            "item_count": self.item_count,
            "iterations": self.iterations,
            "latent_rmse": float(self.latent_rmse),
            "model_code": self.model_code,
            "objective_value": float(self.objective_value),
            "parameter_rmse_mean": float(self.parameter_rmse_mean),
            "request_digest": self.request_digest,
            "result_authority": self.result_authority,
            "rust_device": self.rust_device,
            "sample_size": self.sample_size,
            "seed": self.seed,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact canonical evidence bytes."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


def build_rust_recovery_evidence(
    request: RustExecutionRequest,
    worker_output: Mapping[str, object],
    *,
    completed_at: datetime,
) -> RustRecoveryEvidence:
    """Convert one exact aggregate worker response into governed evidence."""
    request.require_runnable()
    if not isinstance(worker_output, Mapping):
        raise ValueError("worker_output must be a mapping")
    if frozenset(worker_output) != _WORKER_FIELDS:
        raise ValueError("worker_output fields do not match the governed schema")
    summary = worker_output["recovery_summary"]
    if not isinstance(summary, Mapping):
        raise ValueError("recovery_summary must be a mapping")
    if frozenset(summary) != _RECOVERY_FIELDS:
        raise ValueError("recovery_summary fields do not match the governed schema")
    _validate_fixed_text(worker_output["model"], "MLS2PLM", "worker model")
    _validate_fixed_text(worker_output["backend"], request.backend, "worker backend")
    _validate_fixed_text(worker_output["rust_device"], request.rust_device, "worker rust_device")
    for field_name, expected in (
        ("n_persons", request.sample_size),
        ("n_items", request.item_count),
        ("n_clusters", request.cluster_count),
    ):
        if type(worker_output[field_name]) is not type(expected) or worker_output[field_name] != expected:
            raise ValueError(f"worker {field_name} does not match the request")
    evidence_reference = request.execution_reference.replace(
        "validity_execution:", "validity_recovery_evidence:", 1
    )
    return RustRecoveryEvidence(
        evidence_reference=evidence_reference,
        request_digest=request.sha256_digest(),
        fast_mlsirm_revision=request.fast_mlsirm_revision,
        design_code=request.design_code,
        backend=request.backend,
        rust_device=request.rust_device,
        model_code="mlsirm_recovery",
        sample_size=request.sample_size,
        item_count=request.item_count,
        cluster_count=request.cluster_count,
        seed=request.seed,
        convergence_status=worker_output["status"],  # type: ignore[arg-type]
        iterations=worker_output["n_iter"],  # type: ignore[arg-type]
        objective_value=worker_output["objective"],  # type: ignore[arg-type]
        parameter_rmse_mean=summary["parameter_rmse_mean"],  # type: ignore[arg-type]
        latent_rmse=summary["latent_rmse"],  # type: ignore[arg-type]
        distance_rmse=summary["distance_rmse"],  # type: ignore[arg-type]
        gamma_abs_error=summary["gamma_abs_error"],  # type: ignore[arg-type]
        completed_at=completed_at,
    )


__all__ = [
    "RustExecutionRequest",
    "RustRecoveryEvidence",
    "UnsupportedExecutionDesign",
    "build_rust_recovery_evidence",
]
