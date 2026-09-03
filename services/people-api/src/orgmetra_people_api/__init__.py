"""Request-edge, governed read, confirmed-hire, mutation, and operability contracts."""

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
from orgmetra_people_api.operability import (
    PeopleOperabilityAsgiApp,
    PostgresReadinessProbe,
    ReadinessProbe,
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
from orgmetra_people_api.postgres_hire import PostgresHireAcceptancePort
from orgmetra_people_api.postgres_mutations import PostgresPeopleMutationPort

__all__ = [
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
    "PeopleOperabilityAsgiApp",
    "PeopleReadPort",
    "PeopleRecordIntegrityError",
    "PeopleRecordNotFound",
    "PositionMutationCommand",
    "PositionMutationResult",
    "PostgresHireAcceptancePort",
    "PostgresPeopleMutationPort",
    "PostgresPeopleReadPort",
    "PostgresReadinessProbe",
    "ReadinessProbe",
    "AssignmentMutationCommand",
    "AssignmentMutationResult",
    "EmploymentMutationCommand",
    "EmploymentMutationResult",
    "TokenAuthenticator",
    "WorkerPeopleRecord",
    "accept_confirmed_hire",
    "authorize_resource_fields",
    "create_assignment_record",
    "create_employment_record",
    "create_position_record",
    "extract_bearer_token",
    "read_worker_people_record",
]
