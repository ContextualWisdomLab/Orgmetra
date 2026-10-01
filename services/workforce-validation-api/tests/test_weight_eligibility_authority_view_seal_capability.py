"""Hostile sealing-capability regression for weight-eligibility views."""

from uuid import UUID

import pytest

import orgmetra_workforce_validation_api.weight_eligibility_authority as authority_module
from orgmetra_workforce_validation_api.weight_eligibility_authority import (
    WeightEligibilityAuthorityIntegrityError,
    WeightEligibilityAuthorityView,
)

TENANT = UUID("00000000-0000-0000-0000-000000000433")
STUDY = UUID("00000000-0000-0000-0000-000000000434")


def _raw_view_with_module_marker() -> WeightEligibilityAuthorityView:
    """Build the strongest caller-owned exact-runtime forgery available from module state."""
    view = object.__new__(WeightEligibilityAuthorityView)
    object.__setattr__(view, "_tenant_identity", TENANT.int)
    object.__setattr__(view, "_study_identity", STUDY.int)
    object.__setattr__(view, "_fields", (("weight_artifact_digest", "b" * 64),))
    object.__setattr__(
        view,
        "_issuance_marker",
        getattr(authority_module, "_WEIGHT_ELIGIBILITY_VIEW_ISSUANCE_MARKER", object()),
    )
    return view


def test_module_exposes_no_weight_eligibility_view_seal() -> None:
    """Keep the write capability out of ordinary importable module state."""
    assert not hasattr(authority_module, "_WEIGHT_ELIGIBILITY_VIEW_ISSUANCE_MARKER")


def test_importable_marker_cannot_mint_weight_eligibility_view() -> None:
    """Require caller-populated exact objects to remain unreadable."""
    forged_view = _raw_view_with_module_marker()

    with pytest.raises(
        WeightEligibilityAuthorityIntegrityError,
        match="weight-eligibility authority view was not issued by the resolver",
    ):
        _ = forged_view.fields
