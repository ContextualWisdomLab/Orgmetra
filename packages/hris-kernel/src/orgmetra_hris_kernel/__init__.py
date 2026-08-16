"""Tenant- and identity-scoped bitemporal employment-truth kernel.

Use these functions to reconstruct, correct, or reject HR facts inside an
explicit tenant boundary before they are persisted. Persistence,
authorization, and UI stay outside this package.
"""

from orgmetra_hris_kernel.assignment import (
    validate_assignment_employment_coverage,
    validate_assignment_portfolio,
    validate_assignment_position_coverage,
    validate_assignment_write,
    validate_position_seat_capacity,
)
from orgmetra_hris_kernel.correction import close_recorded_interval
from orgmetra_hris_kernel.employment import validate_person_employment_exclusivity
from orgmetra_hris_kernel.errors import (
    AssignmentPortfolioError,
    CorrectionError,
    EmploymentCoverageError,
    EmploymentExclusivityError,
    IdentityScopeError,
    IntervalError,
    KernelError,
    PositionCoverageError,
    PositionSeatError,
    SingleValuedFactError,
)
from orgmetra_hris_kernel.facts import AssignmentFact, EmploymentVersion, PositionVersion
from orgmetra_hris_kernel.intervals import DateInterval, RecordedInterval
from orgmetra_hris_kernel.resolution import resolve_bitemporal_facts, resolve_single_valued_fact

__all__ = [
    "AssignmentFact",
    "AssignmentPortfolioError",
    "CorrectionError",
    "DateInterval",
    "EmploymentCoverageError",
    "EmploymentExclusivityError",
    "EmploymentVersion",
    "IdentityScopeError",
    "IntervalError",
    "KernelError",
    "PositionCoverageError",
    "PositionSeatError",
    "PositionVersion",
    "RecordedInterval",
    "SingleValuedFactError",
    "close_recorded_interval",
    "resolve_bitemporal_facts",
    "resolve_single_valued_fact",
    "validate_assignment_employment_coverage",
    "validate_assignment_portfolio",
    "validate_assignment_position_coverage",
    "validate_assignment_write",
    "validate_person_employment_exclusivity",
    "validate_position_seat_capacity",
]
