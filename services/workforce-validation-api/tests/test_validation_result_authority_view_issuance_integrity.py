"""Regression contract for validation-result view issuance integrity."""

from uuid import UUID

import pytest

from orgmetra_workforce_validation_api.result_authority import (
    ValidationResultAuthorityIntegrityError,
    ValidationResultAuthorityView,
)


TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000f2")


def test_low_level_tuple_construction_cannot_issue_validation_result_view() -> None:
    """Remove tuple's base constructor as an alternate authorized-view issuer."""
    with pytest.raises(TypeError):
        tuple.__new__(
            ValidationResultAuthorityView,
            (
                TENANT.int,
                STUDY.int,
                (("result_digest", "0" * 64),),
            ),
        )


def test_unsealed_object_allocation_cannot_expose_validation_result_view() -> None:
    """Require the resolver seal before raw exact-runtime objects expose state."""
    unsealed = object.__new__(ValidationResultAuthorityView)

    for attribute_name in ("tenant_record_id", "validity_study_id", "fields"):
        with pytest.raises(
            ValidationResultAuthorityIntegrityError,
            match="was not issued by resolve_validation_result_authority",
        ):
            getattr(unsealed, attribute_name)


def test_wrong_issuance_marker_cannot_expose_validation_result_view() -> None:
    """Reject marker-shaped objects that did not originate from the resolver."""
    forged_view = object.__new__(ValidationResultAuthorityView)
    object.__setattr__(forged_view, "_issuance_marker", object())

    with pytest.raises(
        ValidationResultAuthorityIntegrityError,
        match="was not issued by resolve_validation_result_authority",
    ):
        _ = forged_view.fields


def test_raw_validation_result_view_rejects_mutation_and_deletion() -> None:
    """Keep projection state immutable after raw exact-runtime allocation."""
    raw_view = object.__new__(ValidationResultAuthorityView)

    with pytest.raises(AttributeError, match="immutable"):
        raw_view._fields = ()
    with pytest.raises(AttributeError, match="immutable"):
        del raw_view._fields
