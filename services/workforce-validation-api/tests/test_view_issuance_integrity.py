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


def test_low_level_tuple_construction_cannot_expose_authorized_view() -> None:
    """Reject base-constructor views before or at public projection access."""
    payloads = (
        (
            TENANT.int,
            STUDY.int,
            (("study_status_code", "study_closed"),),
        ),
        (
            object(),
            TENANT.int,
            STUDY.int,
            (("study_status_code", "study_closed"),),
        ),
    )

    for payload in payloads:
        try:
            forged = tuple.__new__(registry.ValidityStudyView, payload)
        except TypeError:
            continue
        for attribute in ("tenant_record_id", "validity_study_id", "fields"):
            with pytest.raises(
                registry.ValidityStudyIntegrityError,
                match="was not issued by read_validity_study",
            ):
                getattr(forged, attribute)


def test_unsealed_object_allocation_cannot_expose_authorized_view() -> None:
    """Require the read-path seal even for a raw exact-runtime object allocation."""
    unsealed = object.__new__(registry.ValidityStudyView)

    for attribute in ("tenant_record_id", "validity_study_id", "fields"):
        with pytest.raises(
            registry.ValidityStudyIntegrityError,
            match="was not issued by read_validity_study",
        ):
            getattr(unsealed, attribute)


def test_registry_module_exposes_no_unconditional_view_issuer() -> None:
    """Keep ordinary view issuance inside the authorized read application path."""
    assert not hasattr(registry, "_issue_validity_study_view")
