"""Regression coverage for selection-validity temporal evidence integrity."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo

import pytest

from orgmetra_validity_analysis import (
    ConvergenceDiagnostics,
    MissingnessSummary,
    REVIEWED_FAST_MLSIRM_REVISION,
    ValidationAnalysisHandoff,
    ValidationAnalysisResult,
    build_validation_analysis_handoff,
)
from test_handoff import valid_kwargs
from test_result import result


class ForgedDateTime(datetime):
    """Datetime subclass able to forge canonical validation evidence."""

    def astimezone(self, tz=None):  # type: ignore[no-untyped-def]
        """Keep the hostile subclass alive across UTC normalization."""
        return self

    def isoformat(self, *args, **kwargs) -> str:  # type: ignore[no-untyped-def]
        """Return an instant different from the underlying evidence instant."""
        return "2099-12-31T23:59:59+00:00"


class ForgedReference(str):
    """String subclass able to forge namespace and UUID parsing methods."""

    def startswith(self, prefix, *args):  # type: ignore[no-untyped-def]
        """Pretend that an invalid namespace has the expected prefix."""
        return True

    def split(self, separator=None, maxsplit=-1):  # type: ignore[no-untyped-def]
        """Return a valid UUID suffix while retaining invalid source text."""
        return ["validation_analysis_handoff", "11111111-1111-4111-8111-111111111111"]


class ForgedFixedText(str):
    """String subclass whose comparisons can forge fixed governance values."""

    def __eq__(self, other):  # type: ignore[no-untyped-def]
        """Claim equality with any expected governance text."""
        return True

    def __ne__(self, other):  # type: ignore[no-untyped-def]
        """Claim inequality with no governance text."""
        return False

    def __hash__(self):
        """Use a valid fixed-text hash for set membership forgery tests."""
        return hash("rust_cpu")


class MutableOffset(tzinfo):
    """Timezone fixture whose offset can change after envelope construction."""

    def __init__(self) -> None:
        self.hours = 1

    def utcoffset(self, dt: datetime | None) -> timedelta:
        """Return the currently configured offset."""
        return timedelta(hours=self.hours)

    def dst(self, dt: datetime | None) -> timedelta:
        """Return no daylight-saving offset."""
        return timedelta(0)


class UnknownOffset(tzinfo):
    """Timezone fixture whose UTC offset cannot be resolved."""

    def utcoffset(self, dt: datetime | None) -> None:
        """Return no offset to exercise fail-closed validation."""
        return None

    def dst(self, dt: datetime | None) -> None:
        """Return no daylight-saving offset."""
        return None


class ExplodingOffset(tzinfo):
    """Timezone fixture whose provider raises during offset resolution."""

    def utcoffset(self, dt: datetime | None) -> timedelta:
        """Raise an untrusted provider error."""
        raise RuntimeError("offset provider failed")

    def dst(self, dt: datetime | None) -> timedelta:
        """Return no daylight-saving offset when queried separately."""
        return timedelta(0)


class MutableReal(float):
    """Numeric subclass whose float conversion changes after construction."""

    def __new__(cls, value: float):
        """Create a float-backed value with a separately mutable conversion."""
        instance = super().__new__(cls, value)
        instance.current = value
        return instance

    def __float__(self) -> float:
        """Expose the mutable conversion used by unsafe canonicalization."""
        return self.current


def test_handoff_rejects_datetime_subclass_that_can_forge_requested_at() -> None:
    """Handoff canonical evidence must not invoke caller-overridable datetime methods."""
    with pytest.raises(ValueError, match="requested_at"):
        build_validation_analysis_handoff(
            tenant_record_id="10000000-0000-7000-8000-000000000001",
            handoff_reference="validation_analysis_handoff:11111111-1111-4111-8111-111111111111",
            validation_study_reference="validation_study:22222222-2222-4222-8222-222222222222",
            job_profile_reference="job_profile:33333333-3333-4333-8333-333333333333",
            predictor_snapshot_reference="predictor_snapshot:44444444-4444-4444-8444-444444444444",
            predictor_snapshot_digest="a" * 64,
            criterion_snapshot_reference="criterion_snapshot:55555555-5555-4555-8555-555555555555",
            criterion_snapshot_digest="b" * 64,
            population_snapshot_reference="study_population_snapshot:66666666-6666-4666-8666-666666666666",
            population_snapshot_digest="c" * 64,
            decision_policy_reference="decision_policy:77777777-7777-4777-8777-777777777777",
            decision_policy_digest="d" * 64,
            analysis_plan_reference="validation_analysis_plan:88888888-8888-4888-8888-888888888888",
            analysis_plan_digest="e" * 64,
            actor_reference="actor:99999999-9999-4999-8999-999999999999",
            reviewer_reference="actor:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            fast_mlsirm_revision=REVIEWED_FAST_MLSIRM_REVISION,
            requested_at=ForgedDateTime(2026, 8, 21, 4, 45, tzinfo=timezone.utc),
        )


def test_result_rejects_datetime_subclass_that_can_forge_completed_at() -> None:
    """Result canonical evidence must not invoke caller-overridable datetime methods."""
    with pytest.raises(ValueError, match="completed_at"):
        ValidationAnalysisResult(
            tenant_record_id="10000000-0000-7000-8000-000000000001",
            result_reference="validation_analysis_result:11111111-1111-4111-8111-111111111111",
            handoff_digest="a" * 64,
            provenance_digest="b" * 64,
            fast_mlsirm_revision=REVIEWED_FAST_MLSIRM_REVISION,
            model_code="mlsirm_criterion_related",
            backend="rust_cpu",
            precision="f64",
            effect_estimate=0.42,
            uncertainty_lower=0.10,
            uncertainty_upper=0.70,
            sample_size=12,
            missingness_summary=MissingnessSummary(
                total_observations=12,
                complete_observations=10,
                missing_predictor_observations=1,
                missing_criterion_observations=1,
            ),
            convergence_diagnostics=ConvergenceDiagnostics(
                converged=True,
                iterations=42,
                objective_value=-12.5,
                maximum_gradient=0.0001,
            ),
            completed_at=ForgedDateTime(2026, 8, 21, 4, 45, tzinfo=timezone.utc),
        )


def test_handoff_and_result_detach_mutable_timezone_before_digesting() -> None:
    """Freeze one UTC instant so later timezone mutation cannot rewrite evidence."""
    handoff_zone = MutableOffset()
    handoff_values = valid_kwargs()
    handoff_values["requested_at"] = datetime(2026, 8, 21, 4, 45, tzinfo=handoff_zone)
    handoff = build_validation_analysis_handoff(**handoff_values)
    handoff_before = handoff.canonical_json(), handoff.sha256_digest()
    handoff_zone.hours = 2
    assert (handoff.canonical_json(), handoff.sha256_digest()) == handoff_before

    result_zone = MutableOffset()
    candidate = result(completed_at=datetime(2026, 8, 21, 4, 45, tzinfo=result_zone))
    result_before = candidate.canonical_json(), candidate.sha256_digest()
    result_zone.hours = 2
    assert (candidate.canonical_json(), candidate.sha256_digest()) == result_before


@pytest.mark.parametrize(
    "timestamp",
    [
        datetime.min.replace(tzinfo=timezone(timedelta(hours=1))),
        datetime.max.replace(tzinfo=timezone(-timedelta(hours=1))),
        datetime(2026, 8, 21, 4, 45, tzinfo=UnknownOffset()),
        datetime(2026, 8, 21, 4, 45, tzinfo=ExplodingOffset()),
    ],
)
def test_handoff_rejects_unrepresentable_or_untrusted_timestamp(timestamp: datetime) -> None:
    """Normalize timezone-provider failures and UTC arithmetic overflow at the boundary."""
    values = valid_kwargs()
    values["requested_at"] = timestamp
    with pytest.raises(ValueError, match="requested_at"):
        build_validation_analysis_handoff(**values)


@pytest.mark.parametrize(
    "timestamp",
    [
        datetime.min.replace(tzinfo=timezone(timedelta(hours=1))),
        datetime.max.replace(tzinfo=timezone(-timedelta(hours=1))),
        datetime(2026, 8, 21, 4, 45, tzinfo=UnknownOffset()),
        datetime(2026, 8, 21, 4, 45, tzinfo=ExplodingOffset()),
    ],
)
def test_result_rejects_unrepresentable_or_untrusted_timestamp(timestamp: datetime) -> None:
    """Apply the same fail-closed timestamp contract to completed result evidence."""
    with pytest.raises(ValueError, match="completed_at"):
        result(completed_at=timestamp)


@pytest.mark.parametrize(
    "timestamp",
    [
        ForgedDateTime(2026, 8, 21, 4, 45, tzinfo=timezone.utc),
        datetime(2026, 8, 21, 4, 45, tzinfo=timezone(timedelta(hours=1))),
    ],
)
def test_canonicalization_rejects_low_level_timestamp_reinjection(timestamp: datetime) -> None:
    """Keep canonicalization fail-closed even if an object is corrupted after construction."""
    handoff = build_validation_analysis_handoff(**valid_kwargs())
    object.__setattr__(handoff, "requested_at", timestamp)
    with pytest.raises(ValueError, match="requested_at"):
        handoff.canonical_json()

    candidate = result()
    object.__setattr__(candidate, "completed_at", timestamp)
    with pytest.raises(ValueError, match="completed_at"):
        candidate.canonical_json()


def test_handoff_rejects_runtime_text_subclasses_before_serialization() -> None:
    """Reject text subclasses that can forge reference, digest, code, or fixed-value checks."""
    for field, value in (
        ("tenant_record_id", ForgedFixedText("10000000-0000-7000-8000-000000000001")),
        ("handoff_reference", ForgedReference("wrong_namespace:invalid")),
        ("predictor_snapshot_digest", ForgedFixedText("a" * 64)),
        ("purpose_code", ForgedFixedText("selection_validity_analysis")),
        ("fast_mlsirm_revision", ForgedFixedText(REVIEWED_FAST_MLSIRM_REVISION)),
        ("validation_strategy", ForgedFixedText("criterion_related")),
        ("next_action", ForgedFixedText("governed")),
    ):
        values = valid_kwargs()
        values[field] = value
        with pytest.raises(ValueError, match=field):
            ValidationAnalysisHandoff(**values)


def test_result_snapshots_numeric_values_before_canonicalization() -> None:
    """Detach mutable numeric subclasses before recording scientific evidence bytes."""
    objective = MutableReal(-12.5)
    gradient = MutableReal(0.0001)
    diagnostics = ConvergenceDiagnostics(
        converged=True,
        iterations=42,
        objective_value=objective,
        maximum_gradient=gradient,
    )
    estimate = MutableReal(0.42)
    candidate = result(effect_estimate=estimate, convergence_diagnostics=diagnostics)
    before = candidate.canonical_json(), candidate.sha256_digest()
    objective.current = -1.0
    gradient.current = 0.5
    estimate.current = 0.69
    assert (candidate.canonical_json(), candidate.sha256_digest()) == before


def test_result_rejects_forged_backend_text() -> None:
    """Do not allow a string subclass to forge an allowed backend membership check."""
    with pytest.raises(ValueError, match="backend"):
        result(backend=ForgedFixedText("numpy"))
