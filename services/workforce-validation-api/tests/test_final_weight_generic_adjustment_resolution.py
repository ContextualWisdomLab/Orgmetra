"""Fail closed when a final-weight adjustment has no released owner resolver contract."""

from __future__ import annotations

import pytest

from orgmetra_workforce_validation_api.final_weight_authority import (
    FinalWeightAdjustmentCoordinate,
)


def test_generic_adjustment_without_governed_receipt_locator_is_rejected() -> None:
    """Do not admit a material transform that cannot be re-resolved from owner truth."""
    with pytest.raises(ValueError, match="governed adjustment_code"):
        FinalWeightAdjustmentCoordinate(
            sequence_number=1,
            adjustment_code="custom_transform",
            method_reference="weight_method:custom-transform",
            method_version=1,
            input_weight_artifact_digest="a" * 64,
            output_weight_artifact_digest="b" * 64,
            configuration_digest="c" * 64,
            evidence_receipt_digest="d" * 64,
            evidence_kind="custom_transform_receipt",
        )
