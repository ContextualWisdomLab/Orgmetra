"""Request-edge, governed read, confirmed-hire, and People mutation contracts."""

from orgmetra_people_api.assignment_correction_http import AssignmentCorrectionAsgiApp
from orgmetra_people_api.assignment_correction_mutations import (
    AssignmentCorrectionMutationCommand,
    AssignmentCorrectionMutationPort,
    AssignmentCorrectionMutationResult,
    correct_assignment_record_category,
)
from orgmetra_people_api.auth import (
    AuthenticatedPrincipal,
    AuthenticationFailed,
    TokenAuthenticator,
    extract_bearer_token,
)
from orgmetra_people_api.authorization import authorize_resource_fields
from orgmetra_people_api.hire import (
    HireAcceptanceCommand,
    HireAcceptancePort,
    HireAcceptanceResult,
    HireDecisionIntegrityError,
    HireDecisionNotFound,
    accept_confirmed_hire,
)
from orgmetra_people_api.hire_http import HireAcceptanceAsgiApp
from orgmetra_people_api.http import PeopleAsgiApp
from orgmetra_people_api.mutation_http import PeopleMutationAsgiApp
from orgmetra_people_api.mutations import (
    AssignmentMutationCommand,
    AssignmentMutationResult,
    EmploymentMutationCommand,
    EmploymentMutationResult,
    PeopleMutationIntegrityError,
    PeopleMutationNotFound,
    PeopleMutationPort,
    PositionMutationCommand,
    PositionMutationResult,
    create_assignment_record,
    create_employment_record,
    create_position_record,
)
from orgmetra_people_api.people import (
    AuthorizedWorkerPeopleView,
    PeopleReadPort,
    PeopleRecordIntegrityError,
    PeopleRecordNotFound,
    WorkerPeopleRecord,
    read_worker_people_record,
)
from orgmetra_people_api.postgres import PostgresPeopleReadPort
from orgmetra_people_api.postgres_assignment_corrections import PostgresAssignmentCorrectionMutationPort
from orgmetra_people_api.postgres_hire import PostgresHireAcceptancePort
from orgmetra_people_api.postgres_mutations import PostgresPeopleMutationPort

__all__ = [
    "AssignmentCorrectionAsgiApp",
    "AssignmentCorrectionMutationCommand",
    "AssignmentCorrectionMutationPort",
    "AssignmentCorrectionMutationResult",
    "AuthenticatedPrincipal",
    "AuthenticationFailed",
    "AuthorizedWorkerPeopleView",
    "HireAcceptanceCommand",
    "HireAcceptancePort",
    "HireAcceptanceResult",
    "HireAcceptanceAsgiApp",
    "HireDecisionIntegrityError",
    "HireDecisionNotFound",
    "PeopleAsgiApp",
    "PeopleMutationAsgiApp",
    "PeopleMutationIntegrityError",
    "PeopleMutationNotFound",
    "PeopleMutationPort",
    "PeopleReadPort",
    "PeopleRecordIntegrityError",
    "PeopleRecordNotFound",
    "PositionMutationCommand",
    "PositionMutationResult",
    "PostgresAssignmentCorrectionMutationPort",
    "PostgresHireAcceptancePort",
    "PostgresPeopleMutationPort",
    "PostgresPeopleReadPort",
    "AssignmentMutationCommand",
    "AssignmentMutationResult",
    "EmploymentMutationCommand",
    "EmploymentMutationResult",
    "TokenAuthenticator",
    "WorkerPeopleRecord",
    "accept_confirmed_hire",
    "authorize_resource_fields",
    "correct_assignment_record_category",
    "create_assignment_record",
    "create_employment_record",
    "create_position_record",
    "extract_bearer_token",
    "read_worker_people_record",
]
