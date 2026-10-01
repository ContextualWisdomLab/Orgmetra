"""Regression contract for the complete public authorized-view export census."""

from __future__ import annotations

import orgmetra_workforce_validation_api as api


_EXPECTED_AUTHORIZED_VIEW_NAMES = frozenset(
    {
        "BaseWeightAuthorityView",
        "BaseWeightSupersessionAuthorityView",
        "CalibrationAdjustmentAuthorityView",
        "CalibrationAdjustmentSupersessionAuthorityView",
        "CalibrationAuxiliaryAuthorityView",
        "CalibrationBenchmarkAuthorityView",
        "CalibrationSupportAuthorityView",
        "FinalAnalysisWeightAuthorityView",
        "FinalWeightComponentBindingAuthorityView",
        "FinalWeightSupersessionAuthorityView",
        "NonresponseAdjustmentAuthorityView",
        "NonresponseAdjustmentSupersessionAuthorityView",
        "TrimmingBoundingAuthorityView",
        "TrimmingBoundingSupersessionAuthorityView",
        "ValidationResultAuthorityView",
        "ValidationResultNonVerifiabilitySupersessionAuthorityView",
        "ValidationResultNonVerifiabilitySupersessionV2AuthorityView",
        "ValidationResultNonVerifiabilityView",
        "ValidationResultSupersessionAuthorityView",
        "ValidityStudyView",
        "WeightEligibilityAuthorityView",
        "WeightEligibilitySupersessionAuthorityView",
        "WeightVarianceAuthorityView",
        "WeightVarianceSupersessionAuthorityView",
    }
)


def test_public_authorized_view_export_census_is_explicit_and_non_tuple() -> None:
    """Keep every public authorized projection inside the sealed non-tuple contract."""
    observed = frozenset(name for name in api.__all__ if name.endswith("View"))

    assert observed == _EXPECTED_AUTHORIZED_VIEW_NAMES
    for name in sorted(observed):
        view_type = getattr(api, name)
        assert type(view_type) is type
        assert not issubclass(view_type, tuple)


def test_public_authorized_views_retain_local_sealing_and_mutation_guards() -> None:
    """Require each public authorized projection to keep its local issuance boundary."""
    for name in sorted(_EXPECTED_AUTHORIZED_VIEW_NAMES):
        view_type = getattr(api, name)
        slots = view_type.__dict__.get("__slots__")

        assert type(slots) is tuple
        assert "_issuance_marker" in slots
        assert "__dict__" not in slots
        assert "__new__" in view_type.__dict__
        assert "__setattr__" in view_type.__dict__
        assert "__delattr__" in view_type.__dict__
        assert "_require_issued" in view_type.__dict__
