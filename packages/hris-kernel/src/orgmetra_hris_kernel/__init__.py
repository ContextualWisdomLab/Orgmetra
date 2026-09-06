"""Tenant-scoped bitemporal HRIS, governed audit, job-analysis, and workforce kernel.

Use these contracts to reconstruct, correct, reject, emit governed evidence, or
build PII-minimized descriptive workforce snapshots inside an explicit tenant
boundary before persistence. Persistence, authorization, and UI stay outside
this package.
"""

from orgmetra_hris_kernel.assignment import (
    validate_assignment_employment_coverage,
    validate_assignment_portfolio,
    validate_assignment_position_coverage,
    validate_assignment_write,
    validate_position_seat_capacity,
)
from orgmetra_hris_kernel.audit import AuditOutboxEvent
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
    OrganizationHierarchyError,
    PositionCoverageError,
    PositionSeatError,
    SingleValuedFactError,
)
from orgmetra_hris_kernel.facts import (
    AssignmentFact,
    EmploymentVersion,
    OrganizationUnitVersion,
    PositionVersion,
)
from orgmetra_hris_kernel.intervals import DateInterval, RecordedInterval
from orgmetra_hris_kernel.job_analysis import (
    EvidenceSource,
    FunctionalJobAnalysisProfile,
    JobAnalysisSnapshot,
    KSAORequirement,
    TaskEvidence,
    TaskKSAOLink,
)
from orgmetra_hris_kernel.organization import validate_organization_hierarchy
from orgmetra_hris_kernel.position_reporting import (
    PositionReportingHierarchyError,
    PositionReportingRelationship,
    PositionReportingSnapshot,
    build_position_reporting_snapshot,
)
from orgmetra_hris_kernel.resolution import resolve_bitemporal_facts, resolve_single_valued_fact
from orgmetra_hris_kernel.workforce import (
    WorkforceCompositionSnapshot,
    build_workforce_composition_snapshot,
)

__all__ = [
    "AssignmentFact",
    "AssignmentPortfolioError",
    "AuditOutboxEvent",
    "CorrectionError",
    "DateInterval",
    "EmploymentCoverageError",
    "EmploymentExclusivityError",
    "EmploymentVersion",
    "EvidenceSource",
    "FunctionalJobAnalysisProfile",
    "IdentityScopeError",
    "IntervalError",
    "JobAnalysisSnapshot",
    "KSAORequirement",
    "KernelError",
    "OrganizationHierarchyError",
    "OrganizationUnitVersion",
    "PositionCoverageError",
    "PositionReportingHierarchyError",
    "PositionReportingRelationship",
    "PositionReportingSnapshot",
    "PositionSeatError",
    "PositionVersion",
    "RecordedInterval",
    "SingleValuedFactError",
    "TaskEvidence",
    "TaskKSAOLink",
    "WorkforceCompositionSnapshot",
    "build_position_reporting_snapshot",
    "build_workforce_composition_snapshot",
    "close_recorded_interval",
    "resolve_bitemporal_facts",
    "resolve_single_valued_fact",
    "validate_assignment_employment_coverage",
    "validate_assignment_portfolio",
    "validate_assignment_position_coverage",
    "validate_assignment_write",
    "validate_organization_hierarchy",
    "validate_person_employment_exclusivity",
    "validate_position_seat_capacity",
]
