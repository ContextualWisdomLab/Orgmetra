"""Regression contract for final analysis-weight view issuance integrity."""

from uuid import UUID

import pytest

import orgmetra_workforce_validation_api.final_weight_authority as authority_module
from orgmetra_workforce_validation_api.final_weight_authority import (
    FinalAnalysisWeightAuthorityIntegrityError,
    FinalAnalysisWeightAuthorityView,
)


TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000f1")


def test_importable_marker_cannot_mint_final_weight_view() -> None:
    """Keep the final-weight view seal outside importable module state."""
    marker_name = "_FINAL_ANALYSIS_WEIGHT_VIEW_ISSUANCE_MARKER"
    assert not hasattr(authority_module, marker_name)

    forged_view = object.__new__(FinalAnalysisWeightAuthorityView)
    object.__setattr__(forged_view, "_tenant_identity", TENANT.int)
    object.__setattr__(forged_view, "_study_identity", STUDY.int)
    object.__setattr__(forged_view, "_fields", ())
    object.__setattr__(forged_view, "_issuance_marker", object())

    with pytest.raises(FinalAnalysisWeightAuthorityIntegrityError):
        _ = forged_view.fields


def test_low_level_tuple_construction_cannot_issue_final_weight_view() -> None:
    """Remove tuple's base constructor as an alternate authorized-view issuer."""
    with pytest.raises(TypeError):
        tuple.__new__(
            FinalAnalysisWeightAuthorityView,
            (
                TENANT.int,
                STUDY.int,
                (("analysis_weight_receipt_digest", "6" * 64),),
            ),
        )


def test_unsealed_object_allocation_cannot_expose_final_weight_view() -> None:
    """Require the resolver seal before raw exact-runtime objects expose state."""
    unsealed = object.__new__(FinalAnalysisWeightAuthorityView)

    for attribute_name in ("tenant_record_id", "validity_study_id", "fields"):
        with pytest.raises(
            FinalAnalysisWeightAuthorityIntegrityError,
            match="was not issued by resolve_final_analysis_weight_authority",
        ):
            getattr(unsealed, attribute_name)


def test_wrong_issuance_marker_cannot_expose_final_weight_view() -> None:
    """Reject marker-shaped objects that did not originate from the resolver."""
    forged_view = object.__new__(FinalAnalysisWeightAuthorityView)
    object.__setattr__(forged_view, "_issuance_marker", object())

    with pytest.raises(
        FinalAnalysisWeightAuthorityIntegrityError,
        match="was not issued by resolve_final_analysis_weight_authority",
    ):
        _ = forged_view.fields


def test_raw_final_weight_view_rejects_mutation_and_deletion() -> None:
    """Keep projection state immutable after raw exact-runtime allocation."""
    raw_view = object.__new__(FinalAnalysisWeightAuthorityView)

    with pytest.raises(AttributeError, match="immutable"):
        raw_view._fields = ()
    with pytest.raises(AttributeError, match="immutable"):
        del raw_view._fields
