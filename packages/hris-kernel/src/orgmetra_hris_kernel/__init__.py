"""Identity-scoped bitemporal employment-truth kernel.

Use these functions to reconstruct, correct, or reject HR facts before they
are persisted. Persistence, authorization, and UI stay outside this package.
"""

from orgmetra_hris_kernel.assignment import (
    validate_assignment_employment_coverage,
    validate_assignment_portfolio,
)
from orgmetra_hris_kernel.correction import close_recorded_interval
from orgmetra_hris_kernel.errors import (
    AssignmentPortfolioError,
    CorrectionError,
    EmploymentCoverageError,
    IdentityScopeError,
    IntervalError,
    KernelError,
    SingleValuedFactError,
)
from orgmetra_hris_kernel.facts import AssignmentFact, EmploymentVersion
from orgmetra_hris_kernel.intervals import DateInterval, RecordedInterval
from orgmetra_hris_kernel.resolution import resolve_bitemporal_facts, resolve_single_valued_fact

__all__ = [
    "AssignmentFact",
    "AssignmentPortfolioError",
    "CorrectionError",
    "DateInterval",
    "EmploymentCoverageError",
    "EmploymentVersion",
    "IdentityScopeError",
    "IntervalError",
    "KernelError",
    "RecordedInterval",
    "SingleValuedFactError",
    "close_recorded_interval",
    "resolve_bitemporal_facts",
    "resolve_single_valued_fact",
    "validate_assignment_employment_coverage",
    "validate_assignment_portfolio",
]
