"""Regression contract for weight-eligibility supersession view issuance integrity."""

from uuid import UUID

import pytest

from orgmetra_workforce_validation_api.weight_eligibility_supersession_authority import (
    WeightEligibilitySupersessionAuthorityIntegrityError,
    WeightEligibilitySupersessionAuthorityView,
)


TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000f1")


def test_low_level_tuple_construction_cannot_issue_supersession_view() -> None:
    """Remove tuple's base constructor as an alternate authorized-view issuer."""
    with pytest.raises(TypeError):
        tuple.__new__(
            WeightEligibilitySupersessionAuthorityView,
            (
                TENANT.int,
                STUDY.int,
                (("eligibility_receipt_digest", "6" * 64),),
            ),
        )


def test_unsealed_object_allocation_cannot_expose_supersession_view() -> None:
    """Require the resolver seal before raw exact-runtime objects expose state."""
    unsealed = object.__new__(WeightEligibilitySupersessionAuthorityView)

    for attribute_name in ("tenant_record_id", "validity_study_id", "fields"):
        with pytest.raises(
            WeightEligibilitySupersessionAuthorityIntegrityError,
            match="was not issued by resolve_weight_eligibility_supersession_authority",
        ):
            getattr(unsealed, attribute_name)


def test_wrong_issuance_marker_cannot_expose_supersession_view() -> None:
    """Reject marker-shaped objects that did not originate from the resolver."""
    forged_view = object.__new__(WeightEligibilitySupersessionAuthorityView)
    object.__setattr__(forged_view, "_issuance_marker", object())

    with pytest.raises(
        WeightEligibilitySupersessionAuthorityIntegrityError,
        match="was not issued by resolve_weight_eligibility_supersession_authority",
    ):
        _ = forged_view.fields


def test_raw_supersession_view_rejects_mutation_and_deletion() -> None:
    """Keep projection state immutable after raw exact-runtime allocation."""
    raw_view = object.__new__(WeightEligibilitySupersessionAuthorityView)

    with pytest.raises(AttributeError, match="immutable"):
        raw_view._fields = ()
    with pytest.raises(AttributeError, match="immutable"):
        del raw_view._fields
