"""Regression contracts for target-population and duration-safe weight eligibility."""

from datetime import datetime, timezone

import pytest

from orgmetra_validity_analysis import WeightEligibilityReceipt

TENANT = "10000000-0000-7000-8000-000000000001"
RECEIPT = "weight_eligibility_receipt:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
TARGET = "analysis_target_population:33333333-3333-4333-8333-333333333333"
DURATION = "analysis_reference_duration:77777777-7777-4777-8777-777777777777"
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
DIGEST_D = "d" * 64


def eligibility(**overrides: object) -> WeightEligibilityReceipt:
    """Return one exact longitudinal/cross-sectional weight eligibility receipt."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "receipt_reference": RECEIPT,
        "weight_scope_code": "cross_sectional",
        "target_population_reference": TARGET,
        "target_population_digest": DIGEST_A,
        "reference_duration_reference": DURATION,
        "reference_duration_digest": DIGEST_B,
        "eligible_case_set_digest": DIGEST_C,
        "weight_artifact_digest": DIGEST_D,
        "constructed_at": datetime(2026, 9, 17, 7, 0, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return WeightEligibilityReceipt(**values)


def test_weight_eligibility_receipt_is_deterministic_and_value_minimized() -> None:
    """Bind weight scope, target population, duration, and eligible cases without row values."""
    candidate = eligibility()
    assert candidate.sha256_digest() == eligibility().sha256_digest()
    assert '"weight_scope_code":"cross_sectional"' in candidate.canonical_json()
    assert "weight_value" not in candidate.canonical_json()
    assert repr(candidate) == "WeightEligibilityReceipt(<redacted>)"


@pytest.mark.parametrize("scope", ["monthly", "panel", "opaque", ""])
def test_weight_scope_is_closed_to_cross_sectional_or_longitudinal(scope: str) -> None:
    """Reject caller-defined labels that hide longitudinal/cross-sectional semantics."""
    with pytest.raises(ValueError, match="weight_scope_code"):
        eligibility(weight_scope_code=scope)


def test_weight_eligibility_requires_versioned_population_duration_and_case_evidence() -> None:
    """Reject mutable or opaque population, duration, case-set, and artifact identities."""
    with pytest.raises(ValueError, match="target_population_digest"):
        eligibility(target_population_digest="target-v1")
    with pytest.raises(ValueError, match="reference_duration_reference"):
        eligibility(reference_duration_reference="duration-v1")
    with pytest.raises(ValueError, match="reference_duration_digest"):
        eligibility(reference_duration_digest="duration-v1")
    with pytest.raises(ValueError, match="eligible_case_set_digest"):
        eligibility(eligible_case_set_digest="cases-v1")
    with pytest.raises(ValueError, match="weight_artifact_digest"):
        eligibility(weight_artifact_digest="weight-v1")


def test_evidence_version_is_not_caller_extensible() -> None:
    """Prevent ad hoc receipt schemas from bypassing reviewed weight eligibility semantics."""
    with pytest.raises(ValueError, match="evidence_version"):
        eligibility(evidence_version=2)
