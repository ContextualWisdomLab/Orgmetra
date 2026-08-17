"""Request-edge, governed read, and confirmed-hire contracts for the Orgmetra People API."""

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
from orgmetra_people_api.http import PeopleAsgiApp
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

__all__ = [
    "AuthenticatedPrincipal",
    "AuthenticationFailed",
    "AuthorizedWorkerPeopleView",
    "HireAcceptanceCommand",
    "HireAcceptancePort",
    "HireAcceptanceResult",
    "HireDecisionIntegrityError",
    "HireDecisionNotFound",
    "PeopleAsgiApp",
    "PeopleReadPort",
    "PeopleRecordIntegrityError",
    "PeopleRecordNotFound",
    "PostgresHireAcceptancePort",
    "PostgresPeopleReadPort",
    "TokenAuthenticator",
    "WorkerPeopleRecord",
    "accept_confirmed_hire",
    "authorize_resource_fields",
    "extract_bearer_token",
    "read_worker_people_record",
]
