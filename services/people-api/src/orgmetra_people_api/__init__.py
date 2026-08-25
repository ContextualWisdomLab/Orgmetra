"""Request-edge, governed read, confirmed-hire, and People mutation contracts."""

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
from orgmetra_people_api.postgres_hire import PostgresHireAcceptancePort
from orgmetra_people_api.postgres_mutations import PostgresPeopleMutationPort
from orgmetra_people_api.telemetry import (
    PeopleHttpRequestMeasurement,
    PeopleHttpTelemetryMiddleware,
    classify_people_http_route,
    normalize_http_method,
)

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
    "PeopleHttpRequestMeasurement",
    "PeopleHttpTelemetryMiddleware",
    "PeopleReadPort",
    "PeopleRecordIntegrityError",
    "PeopleRecordNotFound",
    "PositionMutationCommand",
    "PositionMutationResult",
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
    "classify_people_http_route",
    "create_assignment_record",
    "create_employment_record",
    "create_position_record",
    "extract_bearer_token",
    "normalize_http_method",
    "read_worker_people_record",
]
