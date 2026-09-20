"""Hostile sealing-capability regression for nonresponse-adjustment views."""

from uuid import UUID

import pytest

import orgmetra_workforce_validation_api.nonresponse_adjustment_authority as authority_module
from orgmetra_workforce_validation_api.nonresponse_adjustment_authority import (
    NonresponseAdjustmentAuthorityIntegrityError,
    NonresponseAdjustmentAuthorityView,
)

TENANT = UUID("00000000-0000-0000-0000-000000000425")
STUDY = UUID("00000000-0000-0000-0000-000000000426")


def _raw_view_with_module_marker() -> NonresponseAdjustmentAuthorityView:
    """Build the strongest caller-owned exact-runtime forgery available from module state."""
    view = object.__new__(NonresponseAdjustmentAuthorityView)
    object.__setattr__(view, "_tenant_identity", TENANT.int)
    object.__setattr__(view, "_study_identity", STUDY.int)
    object.__setattr__(
        view,
        "_fields",
        (("nonresponse_receipt_digest", "b" * 64),),
    )
    object.__setattr__(
        view,
        "_issuance_marker",
        getattr(
            authority_module,
            "_NONRESPONSE_ADJUSTMENT_VIEW_ISSUANCE_MARKER",
            object(),
        ),
    )
    return view


def test_module_exposes_no_nonresponse_adjustment_view_seal() -> None:
    """Keep the write capability out of ordinary importable module state."""
    assert not hasattr(
        authority_module,
        "_NONRESPONSE_ADJUSTMENT_VIEW_ISSUANCE_MARKER",
    )


def test_importable_marker_cannot_mint_nonresponse_adjustment_view() -> None:
    """Require caller-populated exact objects to remain unreadable."""
    forged_view = _raw_view_with_module_marker()

    with pytest.raises(
        NonresponseAdjustmentAuthorityIntegrityError,
        match=(
            "nonresponse adjustment view was not issued by "
            "resolve_nonresponse_adjustment_authority"
        ),
    ):
        _ = forged_view.fields
