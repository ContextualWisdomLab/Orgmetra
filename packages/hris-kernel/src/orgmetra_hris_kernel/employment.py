"""Exclusive versus concurrent employment rules for one tenant-scoped person."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from orgmetra_hris_kernel.errors import EmploymentExclusivityError
from orgmetra_hris_kernel.facts import EmploymentVersion

_EXCLUSIVE = "exclusive"
_KNOWN_CONCURRENCY = frozenset({_EXCLUSIVE, "concurrent"})


def validate_person_employment_exclusivity(
    employment_versions: list[EmploymentVersion],
    *,
    tenant_record_id: UUID,
    person_record_id: UUID,
    known_at: datetime,
) -> None:
    """Reject overlapping exclusive jobs for one person inside one tenant.

    A second job must be marked ``concurrent``. A later exclusive employment is
    legal only after the prior exclusive period ends. Identical person or
    employment identifiers from another tenant are outside this decision scope.

    Args:
        employment_versions: Candidate versions, including other tenants and people.
        tenant_record_id: Tenant namespace whose employment portfolio is reviewed.
        person_record_id: Worker whose jobs are being saved.
        known_at: The knowledge cutoff used for the review.

    Raises:
        EmploymentExclusivityError: Mark the second job concurrent, or close the
            prior exclusive period, then save.
    """
    scoped = [
        version
        for version in employment_versions
        if version.tenant_record_id == tenant_record_id
        and version.person_record_id == person_record_id
    ]
    for version in scoped:
        if version.employment_concurrency_code not in _KNOWN_CONCURRENCY:
            raise EmploymentExclusivityError(
                "employment_concurrency_code must be exclusive or concurrent.",
                next_action="Choose exclusive or concurrent, then save the employment.",
            )
    visible_exclusive = [
        version
        for version in scoped
        if version.recorded.contains(known_at)
        and version.employment_concurrency_code == _EXCLUSIVE
    ]
    for index, left in enumerate(visible_exclusive):
        for right in visible_exclusive[index + 1 :]:
            if left.employment_record_id == right.employment_record_id:
                continue
            if left.effective.overlaps(right.effective):
                raise EmploymentExclusivityError(
                    "Two exclusive employments overlap for one person in this tenant.",
                    next_action="Mark the second job concurrent or close the prior exclusive period, then save.",
                )
