"""Hostile sealing-capability regression for final-weight supersession views."""

from uuid import UUID

import pytest

import orgmetra_workforce_validation_api.final_weight_supersession_authority as authority_module
from orgmetra_workforce_validation_api.final_weight_supersession_authority import (
    FinalWeightSupersessionAuthorityIntegrityError,
    FinalWeightSupersessionAuthorityView,
)

TENANT = UUID("00000000-0000-0000-0000-000000000421")
STUDY = UUID("00000000-0000-0000-0000-000000000422")


def _raw_view_with_module_marker() -> FinalWeightSupersessionAuthorityView:
    """Build the strongest caller-owned exact-runtime forgery available from module state."""
    view = object.__new__(FinalWeightSupersessionAuthorityView)
    object.__setattr__(view, "_tenant_identity", TENANT.int)
    object.__setattr__(view, "_study_identity", STUDY.int)
    object.__setattr__(
        view,
        "_fields",
        (("analysis_weight_receipt_digest", "a" * 64),),
    )
    object.__setattr__(
        view,
        "_issuance_marker",
        getattr(
            authority_module,
            "_FINAL_WEIGHT_SUPERSESSION_VIEW_ISSUANCE_MARKER",
            object(),
        ),
    )
    return view


def test_module_exposes_no_final_weight_supersession_view_seal() -> None:
    """Keep the write capability out of ordinary importable module state."""
    assert not hasattr(
        authority_module,
        "_FINAL_WEIGHT_SUPERSESSION_VIEW_ISSUANCE_MARKER",
    )


def test_importable_marker_cannot_mint_final_weight_supersession_view() -> None:
    """Require caller-populated exact objects to remain unreadable."""
    forged_view = _raw_view_with_module_marker()

    with pytest.raises(
        FinalWeightSupersessionAuthorityIntegrityError,
        match=(
            "final-weight supersession view was not issued by "
            "resolve_final_weight_supersession_authority"
        ),
    ):
        _ = forged_view.fields
