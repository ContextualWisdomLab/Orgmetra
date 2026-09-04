"""Regression tests for post-construction structured-interview plan integrity."""

from copy import copy
from dataclasses import fields, replace
from datetime import datetime, timedelta, tzinfo

import pytest

import orgmetra_interview_plan.plan as plan_module
from test_activation import plan


class ReentrantPlanAllocatorTimezone(tzinfo):
    """Retain a plan allocated reentrantly from a caller-owned timezone callback."""

    def __init__(self) -> None:
        """Start without a retained forged plan."""
        self.forged_plan: object | None = None

    def utcoffset(self, _dt: datetime | None) -> timedelta:
        """Allocate once while the legitimate constructor normalizes generated_at."""
        if self.forged_plan is None:
            self.forged_plan = plan_module.StructuredInterviewPlan.__new__(
                plan_module.StructuredInterviewPlan
            )
        return timedelta(hours=9)

    def dst(self, _dt: datetime | None) -> timedelta:
        """Use a stable zero daylight-saving offset."""
        return timedelta(0)

    def tzname(self, _dt: datetime | None) -> str:
        """Return a descriptive test-only timezone name."""
        return "REENTRANT"


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


def test_object_new_clone_cannot_acquire_plan_issuance_evidence():
    """An object.__new__ clone must not mint fresh creation evidence."""
    issued_plan = plan()
    forged_plan = object.__new__(type(issued_plan))
    for field in fields(issued_plan):
        object.__setattr__(forged_plan, field.name, getattr(issued_plan, field.name))

    with pytest.raises(ValueError, match="constructor provenance is unavailable"):
        forged_plan.__post_init__()
    with pytest.raises(ValueError, match="issuance evidence is unavailable"):
        forged_plan.canonical_json()


def test_direct_class_new_clone_cannot_acquire_plan_issuance_evidence():
    """Calling the class allocator directly must not grant constructor provenance."""
    issued_plan = plan()
    forged_plan = type(issued_plan).__new__(type(issued_plan))
    for field in fields(issued_plan):
        object.__setattr__(forged_plan, field.name, getattr(issued_plan, field.name))

    with pytest.raises(ValueError, match="constructor provenance is unavailable"):
        forged_plan.__post_init__()
    with pytest.raises(ValueError, match="issuance evidence is unavailable"):
        forged_plan.canonical_json()


def test_timezone_callback_cannot_mint_plan_constructor_provenance():
    """Caller timezone code must not retain constructor privilege for another plan."""
    callback_timezone = ReentrantPlanAllocatorTimezone()
    issued_plan = replace(
        plan(),
        generated_at=datetime(2026, 8, 30, 12, 0, tzinfo=callback_timezone),
    )
    forged_plan = callback_timezone.forged_plan
    assert forged_plan is not None

    for field in fields(issued_plan):
        object.__setattr__(forged_plan, field.name, getattr(issued_plan, field.name))

    with pytest.raises(ValueError, match="constructor provenance is unavailable"):
        forged_plan.__post_init__()
    with pytest.raises(ValueError, match="issuance evidence is unavailable"):
        forged_plan.canonical_json()


def test_existing_plan_seal_cannot_be_replaced_by_secondary_registration():
    """A second seal registration must not overwrite an already issued plan."""
    issued_plan = plan()
    original_json = issued_plan.canonical_json()

    with pytest.raises(ValueError, match="issuance evidence already exists"):
        plan_module._register_plan_seal(issued_plan, "0" * 64)

    assert issued_plan.canonical_json() == original_json
