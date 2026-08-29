"""Regression tests for post-construction structured-interview plan integrity."""

from copy import copy

import pytest

import orgmetra_interview_plan.plan as plan_module
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


def test_missing_process_local_plan_issuance_evidence_fails_closed():
    """Canonical export requires the creation-bound process-local plan seal."""
    candidate_plan = plan()
    plan_module._discard_plan_seal(id(candidate_plan))

    with pytest.raises(ValueError, match="issuance evidence is unavailable"):
        candidate_plan.canonical_json()
    with pytest.raises(ValueError, match="issuance evidence is unavailable"):
        candidate_plan.sha256_digest()


def test_copied_plan_has_no_transferable_process_local_issuance_evidence():
    """Copying fields must not manufacture a second issued plan identity."""
    copied_plan = copy(plan())

    with pytest.raises(ValueError, match="issuance evidence is unavailable"):
        copied_plan.canonical_json()
    with pytest.raises(ValueError, match="issuance evidence is unavailable"):
        copied_plan.sha256_digest()
