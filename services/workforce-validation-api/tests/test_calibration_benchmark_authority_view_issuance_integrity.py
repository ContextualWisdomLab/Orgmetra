"""Regression contract for calibration-benchmark authorized-view issuance integrity."""

from uuid import UUID

import pytest

from orgmetra_workforce_validation_api.benchmark_authority import (
    CalibrationBenchmarkAuthorityIntegrityError,
    CalibrationBenchmarkAuthorityView,
)


TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000f1")


def test_low_level_tuple_construction_cannot_issue_calibration_benchmark_view() -> None:
    """Remove tuple's base constructor as an alternate authorized-view issuer."""
    with pytest.raises(TypeError):
        tuple.__new__(
            CalibrationBenchmarkAuthorityView,
            (
                TENANT.int,
                STUDY.int,
                (("benchmark_receipt_digest", "6" * 64),),
            ),
        )


def test_unsealed_object_allocation_cannot_expose_calibration_benchmark_view() -> None:
    """Require the resolver seal before any raw exact-runtime object exposes state."""
    unsealed = object.__new__(CalibrationBenchmarkAuthorityView)

    for attribute in ("tenant_record_id", "validity_study_id", "fields"):
        with pytest.raises(
            CalibrationBenchmarkAuthorityIntegrityError,
            match="was not issued by resolve_calibration_benchmark_authority",
        ):
            getattr(unsealed, attribute)


def test_wrong_issuance_marker_cannot_expose_calibration_benchmark_view() -> None:
    """Reject marker-shaped raw objects that did not originate from the resolver."""
    forged = object.__new__(CalibrationBenchmarkAuthorityView)
    object.__setattr__(forged, "_issuance_marker", object())

    with pytest.raises(
        CalibrationBenchmarkAuthorityIntegrityError,
        match="was not issued by resolve_calibration_benchmark_authority",
    ):
        _ = forged.fields


def test_raw_calibration_benchmark_view_rejects_public_mutation_and_deletion() -> None:
    """Keep projection state immutable even when callers allocate the exact runtime type."""
    raw = object.__new__(CalibrationBenchmarkAuthorityView)

    with pytest.raises(AttributeError, match="immutable"):
        raw._fields = ()
    with pytest.raises(AttributeError, match="immutable"):
        del raw._fields
