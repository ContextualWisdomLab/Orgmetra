"""Regression contract for workforce-validation authorized-view issuance."""

from uuid import UUID

import pytest

import orgmetra_workforce_validation_api.registry as registry


TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000c1")


def test_direct_authorized_view_construction_fails_closed() -> None:
    """Require purpose-bound reads, not public construction, to issue study views."""
    with pytest.raises(TypeError, match="issued only by read_validity_study"):
        registry.ValidityStudyView(
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            fields=(("study_status_code", "study_draft"),),
        )


def test_registry_module_exposes_no_unconditional_view_issuer() -> None:
    """Keep ordinary view issuance inside the authorized read application path."""
    assert not hasattr(registry, "_issue_validity_study_view")


def test_low_level_tuple_construction_cannot_issue_study_view() -> None:
    """Remove tuple's base constructor as an alternate authorized-view issuer."""
    with pytest.raises(TypeError):
        tuple.__new__(
            registry.ValidityStudyView,
            (TENANT.int, STUDY.int, (("study_status_code", "study_draft"),)),
        )


def test_unsealed_object_allocation_cannot_expose_study_view() -> None:
    """Require the read-path seal before raw exact-runtime objects expose state."""
    unsealed = object.__new__(registry.ValidityStudyView)

    for attribute_name in ("tenant_record_id", "validity_study_id", "fields"):
        with pytest.raises(
            registry.ValidityStudyIntegrityError,
            match="was not issued by read_validity_study",
        ):
            getattr(unsealed, attribute_name)


def test_wrong_issuance_marker_cannot_expose_study_view() -> None:
    """Reject marker-shaped objects that did not originate from the read path."""
    forged_view = object.__new__(registry.ValidityStudyView)
    object.__setattr__(forged_view, "_issuance_marker", object())

    with pytest.raises(
        registry.ValidityStudyIntegrityError,
        match="was not issued by read_validity_study",
    ):
        _ = forged_view.fields


def test_raw_study_view_rejects_mutation_and_deletion() -> None:
    """Keep projection state immutable after raw exact-runtime allocation."""
    raw_view = object.__new__(registry.ValidityStudyView)

    with pytest.raises(AttributeError, match="immutable"):
        raw_view._fields = ()
    with pytest.raises(AttributeError, match="immutable"):
        del raw_view._fields
