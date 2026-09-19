"""Regression contract for base-weight authorized-view issuance integrity."""

from uuid import UUID

import pytest

import orgmetra_workforce_validation_api.base_weight_authority as authority_module
from orgmetra_workforce_validation_api.base_weight_authority import (
    BaseWeightAuthorityIntegrityError,
    BaseWeightAuthorityView,
)


TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000f1")


def test_low_level_tuple_construction_cannot_issue_base_weight_view() -> None:
    """Remove tuple's base constructor as an alternate authorized-view issuer."""
    with pytest.raises(TypeError):
        tuple.__new__(
            BaseWeightAuthorityView,
            (
                TENANT.int,
                STUDY.int,
                (("base_weight_artifact_digest", "6" * 64),),
            ),
        )


def test_unsealed_object_allocation_cannot_expose_base_weight_view() -> None:
    """Require the resolver seal before any raw exact-runtime object exposes state."""
    unsealed = object.__new__(BaseWeightAuthorityView)

    for attribute in ("tenant_record_id", "validity_study_id", "fields"):
        with pytest.raises(
            BaseWeightAuthorityIntegrityError,
            match="was not issued by resolve_base_weight_authority",
        ):
            getattr(unsealed, attribute)


def test_wrong_issuance_marker_cannot_expose_base_weight_view() -> None:
    """Reject marker-shaped raw objects that did not originate from the resolver."""
    forged = object.__new__(BaseWeightAuthorityView)
    object.__setattr__(forged, "_issuance_marker", object())

    with pytest.raises(
        BaseWeightAuthorityIntegrityError,
        match="was not issued by resolve_base_weight_authority",
    ):
        _ = forged.fields


def test_importable_marker_cannot_mint_base_weight_view() -> None:
    """Reject a caller-populated view and keep its sealing capability out of module state."""
    assert not hasattr(authority_module, "_BASE_WEIGHT_AUTHORITY_VIEW_ISSUANCE_MARKER")
    forged = object.__new__(BaseWeightAuthorityView)
    object.__setattr__(forged, "_tenant_identity", TENANT.int)
    object.__setattr__(forged, "_study_identity", STUDY.int)
    object.__setattr__(
        forged,
        "_fields",
        (("base_weight_artifact_digest", "6" * 64),),
    )
    object.__setattr__(
        forged,
        "_issuance_marker",
        getattr(
            authority_module,
            "_BASE_WEIGHT_AUTHORITY_VIEW_ISSUANCE_MARKER",
            object(),
        ),
    )

    with pytest.raises(
        BaseWeightAuthorityIntegrityError,
        match="was not issued by resolve_base_weight_authority",
    ):
        _ = forged.fields


def test_raw_base_weight_view_rejects_public_mutation_and_deletion() -> None:
    """Keep projection state immutable even when callers allocate the exact runtime type."""
    raw = object.__new__(BaseWeightAuthorityView)

    with pytest.raises(AttributeError, match="immutable"):
        raw._fields = ()
    with pytest.raises(AttributeError, match="immutable"):
        del raw._fields
