"""Regression contract for calibration-benchmark view issuance integrity."""

from uuid import UUID

import pytest

import orgmetra_workforce_validation_api.benchmark_authority as authority_module
from orgmetra_workforce_validation_api.benchmark_authority import (
    CalibrationBenchmarkAuthorityIntegrityError,
    CalibrationBenchmarkAuthorityView,
)


TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000f2")


def test_importable_marker_cannot_mint_calibration_benchmark_view() -> None:
    """Keep the benchmark view seal outside importable module state."""
    marker_name = "_CALIBRATION_BENCHMARK_VIEW_ISSUANCE_MARKER"
    assert not hasattr(authority_module, marker_name)

    forged_view = object.__new__(CalibrationBenchmarkAuthorityView)
    object.__setattr__(forged_view, "_tenant_identity", TENANT.int)
    object.__setattr__(forged_view, "_study_identity", STUDY.int)
    object.__setattr__(forged_view, "_fields", ())
    object.__setattr__(forged_view, "_issuance_marker", object())

    with pytest.raises(CalibrationBenchmarkAuthorityIntegrityError):
        _ = forged_view.fields


def test_low_level_tuple_construction_cannot_issue_benchmark_view() -> None:
    """Remove tuple's base constructor as an alternate authorized-view issuer."""
    with pytest.raises(TypeError):
        tuple.__new__(
            CalibrationBenchmarkAuthorityView,
            (TENANT.int, STUDY.int, (("benchmark_receipt_digest", "0" * 64),)),
        )


def test_unsealed_object_allocation_cannot_expose_benchmark_view() -> None:
    """Require the resolver seal before raw exact-runtime objects expose state."""
    unsealed = object.__new__(CalibrationBenchmarkAuthorityView)

    for attribute_name in ("tenant_record_id", "validity_study_id", "fields"):
        with pytest.raises(
            CalibrationBenchmarkAuthorityIntegrityError,
            match="was not issued by resolve_calibration_benchmark_authority",
        ):
            getattr(unsealed, attribute_name)


def test_wrong_issuance_marker_cannot_expose_benchmark_view() -> None:
    """Reject marker-shaped objects that did not originate from the resolver."""
    forged_view = object.__new__(CalibrationBenchmarkAuthorityView)
    object.__setattr__(forged_view, "_issuance_marker", object())

    with pytest.raises(
        CalibrationBenchmarkAuthorityIntegrityError,
        match="was not issued by resolve_calibration_benchmark_authority",
    ):
        _ = forged_view.fields


def test_raw_benchmark_view_rejects_mutation_and_deletion() -> None:
    """Keep projection state immutable after raw exact-runtime allocation."""
    raw_view = object.__new__(CalibrationBenchmarkAuthorityView)

    with pytest.raises(AttributeError, match="immutable"):
        raw_view._fields = ()
    with pytest.raises(AttributeError, match="immutable"):
        del raw_view._fields
