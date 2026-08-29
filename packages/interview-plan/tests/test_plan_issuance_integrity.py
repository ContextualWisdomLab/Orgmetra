"""Regression tests for post-construction structured-interview plan integrity."""

from copy import copy

import pytest

from test_activation import plan


def test_plan_canonical_evidence_fails_closed_after_low_level_mutation():
    """A built plan must not export different canonical evidence after issuance."""
    candidate_plan = plan()
    original_json = candidate_plan.canonical_json()
    original_digest = candidate_plan.sha256_digest()

    object.__setattr__(
        candidate_plan,
        "question_count",
        candidate_plan.question_count - 1,
    )

    with pytest.raises(ValueError, match="changed after plan issuance"):
        candidate_plan.canonical_json()
    with pytest.raises(ValueError, match="changed after plan issuance"):
        candidate_plan.sha256_digest()

    assert original_json
    assert len(original_digest) == 64


def test_copied_plan_has_no_transferable_process_local_issuance_evidence():
    """Copying fields must not manufacture a second issued plan identity."""
    copied_plan = copy(plan())

    with pytest.raises(ValueError, match="issuance evidence is unavailable"):
        copied_plan.canonical_json()
    with pytest.raises(ValueError, match="issuance evidence is unavailable"):
        copied_plan.sha256_digest()
