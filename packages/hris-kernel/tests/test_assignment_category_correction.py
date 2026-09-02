"""Assignment category correction and supersession regressions."""

from dataclasses import replace
from uuid import UUID

import pytest

from orgmetra_hris_kernel import (
    AssignmentSupersessionFact,
    CorrectionError,
    RecordedInterval,
    correct_assignment_category,
)

from .conftest import recorded, utc

SUPERSESSION = UUID("10000000-0000-7000-8000-000000000390")
REPLACEMENT = UUID("10000000-0000-7000-8000-000000000391")


class ForgedCategory(str):
    """Represent caller-controlled string behavior at the correction boundary."""


def test_category_correction_closes_and_links_an_immutable_replacement(
    jordan_icu_assignment,
) -> None:
    """Correction preserves Assignment semantics while replacing category truth."""
    predecessor = replace(jordan_icu_assignment, assignment_category_code="primary")
    corrected_at = utc(2024, 6, 1, 12)

    closed, replacement, supersession = correct_assignment_category(
        predecessor,
        replacement_assignment_record_id=REPLACEMENT,
        assignment_supersession_record_id=SUPERSESSION,
        corrected_category_code="concurrent_secondary",
        recorded_at=corrected_at,
    )

    assert closed.assignment_record_id == predecessor.assignment_record_id
    assert closed.recorded.start == predecessor.recorded.start
    assert closed.recorded.end == corrected_at
    assert replacement.assignment_record_id == REPLACEMENT
    assert replacement.tenant_record_id == predecessor.tenant_record_id
    assert replacement.employment_record_id == predecessor.employment_record_id
    assert replacement.person_record_id == predecessor.person_record_id
    assert replacement.position_record_id == predecessor.position_record_id
    assert replacement.allocation_ratio == predecessor.allocation_ratio
    assert replacement.effective == predecessor.effective
    assert replacement.recorded == RecordedInterval(start=corrected_at)
    assert replacement.assignment_category_code == "concurrent_secondary"
    assert supersession == AssignmentSupersessionFact(
        tenant_record_id=predecessor.tenant_record_id,
        assignment_supersession_record_id=SUPERSESSION,
        predecessor_assignment_record_id=predecessor.assignment_record_id,
        replacement_assignment_record_id=REPLACEMENT,
        recorded_at=corrected_at,
    )


@pytest.mark.parametrize(
    "predecessor_category",
    ["legacy_unspecified", "secondary", ForgedCategory("primary")],
)
def test_category_correction_rejects_non_explicit_predecessor_categories(
    jordan_icu_assignment,
    predecessor_category,
) -> None:
    """This correction contract starts only from exact committed explicit category truth."""
    predecessor = replace(
        jordan_icu_assignment,
        assignment_category_code=predecessor_category,
    )

    with pytest.raises(CorrectionError, match="explicit governed category"):
        correct_assignment_category(
            predecessor,
            replacement_assignment_record_id=REPLACEMENT,
            assignment_supersession_record_id=SUPERSESSION,
            corrected_category_code="primary",
            recorded_at=utc(2024, 6, 1, 12),
        )


@pytest.mark.parametrize(
    "corrected_category_code",
    ["legacy_unspecified", "secondary", ForgedCategory("concurrent_secondary")],
)
def test_category_correction_rejects_non_operational_target_categories(
    jordan_icu_assignment,
    corrected_category_code,
) -> None:
    """A correction target is an exact explicit category, never a sentinel or alias."""
    predecessor = replace(jordan_icu_assignment, assignment_category_code="primary")

    with pytest.raises(CorrectionError, match="corrected category"):
        correct_assignment_category(
            predecessor,
            replacement_assignment_record_id=REPLACEMENT,
            assignment_supersession_record_id=SUPERSESSION,
            corrected_category_code=corrected_category_code,
            recorded_at=utc(2024, 6, 1, 12),
        )


def test_category_correction_rejects_noop_and_identity_reuse(jordan_icu_assignment) -> None:
    """A correction must change category truth and allocate a new Assignment identity."""
    predecessor = replace(jordan_icu_assignment, assignment_category_code="primary")

    with pytest.raises(CorrectionError, match="different category"):
        correct_assignment_category(
            predecessor,
            replacement_assignment_record_id=REPLACEMENT,
            assignment_supersession_record_id=SUPERSESSION,
            corrected_category_code="primary",
            recorded_at=utc(2024, 6, 1, 12),
        )
    with pytest.raises(CorrectionError, match="replacement Assignment identity"):
        correct_assignment_category(
            predecessor,
            replacement_assignment_record_id=predecessor.assignment_record_id,
            assignment_supersession_record_id=SUPERSESSION,
            corrected_category_code="concurrent_secondary",
            recorded_at=utc(2024, 6, 1, 12),
        )


def test_category_correction_rejects_already_closed_predecessor(jordan_icu_assignment) -> None:
    """Only the currently recorded-open fact can be superseded by this operation."""
    predecessor = replace(
        jordan_icu_assignment,
        assignment_category_code="primary",
        recorded=recorded(utc(2024, 3, 1, 16), utc(2024, 5, 1, 16)),
    )

    with pytest.raises(CorrectionError, match="already closed"):
        correct_assignment_category(
            predecessor,
            replacement_assignment_record_id=REPLACEMENT,
            assignment_supersession_record_id=SUPERSESSION,
            corrected_category_code="concurrent_secondary",
            recorded_at=utc(2024, 6, 1, 12),
        )


def test_category_correction_rejects_non_forward_recorded_time(jordan_icu_assignment) -> None:
    """Supersession cannot close history at or before the predecessor recorded start."""
    predecessor = replace(jordan_icu_assignment, assignment_category_code="primary")

    with pytest.raises(CorrectionError, match="strictly later"):
        correct_assignment_category(
            predecessor,
            replacement_assignment_record_id=REPLACEMENT,
            assignment_supersession_record_id=SUPERSESSION,
            corrected_category_code="concurrent_secondary",
            recorded_at=predecessor.recorded.start,
        )
