"""RED contracts for reproducible trimming and bounding weight adjustments."""

from datetime import datetime, timezone

import pytest

from orgmetra_validity_analysis import AnalysisWeightAdjustment, TrimmingBoundingAdjustmentReceipt

TENANT = "10000000-0000-7000-8000-000000000001"
RECEIPT = "trimming_bounding_adjustment_receipt:11111111-1111-4111-8111-111111111111"
RULE = "weight_trimming_rule:22222222-2222-4222-8222-222222222222"
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
DIGEST_D = "d" * 64


def trimming_receipt(**overrides: object) -> TrimmingBoundingAdjustmentReceipt:
    """Return one value-minimized trimming/bounding provenance receipt."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "receipt_reference": RECEIPT,
        "rule_reference": RULE,
        "rule_version": 1,
        "rule_configuration_digest": DIGEST_A,
        "affected_case_occurrence_set_digest": DIGEST_B,
        "affected_case_count": 3,
        "input_weight_artifact_digest": DIGEST_C,
        "output_weight_artifact_digest": DIGEST_D,
        "constructed_at": datetime(2026, 9, 17, 5, 40, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return TrimmingBoundingAdjustmentReceipt(**values)


def test_trimming_receipt_is_deterministic_value_minimized_and_redacted() -> None:
    """Preserve threshold/rule and affected-case provenance without row weights."""
    candidate = trimming_receipt()
    assert candidate.sha256_digest() == trimming_receipt().sha256_digest()
    assert f'"rule_configuration_digest":"{DIGEST_A}"' in candidate.canonical_json()
    assert f'"affected_case_occurrence_set_digest":"{DIGEST_B}"' in candidate.canonical_json()
    assert "weight_value" not in candidate.canonical_json()
    assert repr(candidate) == "TrimmingBoundingAdjustmentReceipt(<redacted>)"


def test_trimming_adjustment_requires_typed_receipt_kind() -> None:
    """Do not let trimming hide behind a generic opaque adjustment receipt."""
    with pytest.raises(ValueError, match="trimming_bounding_adjustment_receipt"):
        AnalysisWeightAdjustment(
            sequence_number=1,
            adjustment_code="weight_trimming_adjustment",
            method_reference="weight_method:33333333-3333-4333-8333-333333333333",
            method_version=1,
            input_weight_artifact_digest=DIGEST_C,
            output_weight_artifact_digest=DIGEST_D,
            configuration_digest=DIGEST_A,
            evidence_receipt_digest=DIGEST_B,
            evidence_kind="generic_adjustment_receipt",
        )


def test_bounding_adjustment_accepts_typed_receipt_kind() -> None:
    """Allow a bound transform only when its evidence family is explicit."""
    adjustment = AnalysisWeightAdjustment(
        sequence_number=1,
        adjustment_code="weight_bounding_adjustment",
        method_reference="weight_method:33333333-3333-4333-8333-333333333333",
        method_version=1,
        input_weight_artifact_digest=DIGEST_C,
        output_weight_artifact_digest=DIGEST_D,
        configuration_digest=DIGEST_A,
        evidence_receipt_digest=trimming_receipt().sha256_digest(),
        evidence_kind="trimming_bounding_adjustment_receipt",
    )
    assert adjustment.evidence_kind == "trimming_bounding_adjustment_receipt"


def test_receipt_rejects_missing_or_nonreproducible_rule_evidence() -> None:
    """Fail closed when the rule version/configuration or affected cases are not reproducible."""
    with pytest.raises(ValueError, match="rule_version"):
        trimming_receipt(rule_version=0)
    with pytest.raises(ValueError, match="rule_configuration_digest"):
        trimming_receipt(rule_configuration_digest="floating")
    with pytest.raises(ValueError, match="affected_case_occurrence_set_digest"):
        trimming_receipt(affected_case_occurrence_set_digest="missing")
    with pytest.raises(ValueError, match="affected_case_count"):
        trimming_receipt(affected_case_count=0)


def test_receipt_rejects_noop_or_extensible_schema() -> None:
    """A declared transform must change artifact identity under the reviewed schema."""
    with pytest.raises(ValueError, match="output_weight_artifact_digest"):
        trimming_receipt(output_weight_artifact_digest=DIGEST_C)
    with pytest.raises(ValueError, match="evidence_version"):
        trimming_receipt(evidence_version=2)
