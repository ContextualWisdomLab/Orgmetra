"""FastAPI composition for the first purpose-bound Orgmetra HTTP slice."""

from collections.abc import Callable
from functools import partial
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Header, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.concurrency import run_in_threadpool

from orgmetra_postgres import PurposeContext

from .auth import (
    AuthorizedPrincipal,
    AuthenticationFailed,
    TokenAuthorizer,
    ensure_purpose_authorized,
    ensure_scope_authorized,
    extract_bearer_token,
)
from .middleware import RequestBoundaryMiddleware
from .problems import InvalidRequestMetadata, ResourceNotFound, register_exception_handlers
from .repository import PeopleRepository
from .schemas import (
    AuditEventListResponse,
    AuditEventResponse,
    CandidateCreateRequest,
    CandidateResponse,
    CandidateWorkerLinkCreateRequest,
    CandidateWorkerLinkResponse,
    EmploymentCreateRequest,
    EmploymentResponse,
    HealthResponse,
    PersonCreateRequest,
    PersonResponse,
)

IdentifierFactory = Callable[[], UUID]
_BEARER_SCHEME = HTTPBearer(auto_error=False, scheme_name="KeyverseBearer")


class RequiredPurpose:
    """Resolve one authenticated route scope and business purpose."""

    def __init__(self, scope_code: str, purpose_code: str) -> None:
        """Store route-owned capability and purpose codes."""

        self._scope_code = scope_code
        self._purpose_code = purpose_code

    async def __call__(
        self,
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Security(_BEARER_SCHEME),
        correlation_header: str | None = Header(default=None, alias="X-Correlation-Id"),
    ) -> PurposeContext:
        """Authenticate, authorize two dimensions, and return repository context."""

        authorization_value = None
        if credentials is not None:
            authorization_value = f"{credentials.scheme} {credentials.credentials}"
        bearer_token = extract_bearer_token(authorization_value)
        authorizer: TokenAuthorizer = request.app.state.token_authorizer
        principal = await authorizer.authorize(
            bearer_token,
            self._scope_code,
            self._purpose_code,
        )
        if not isinstance(principal, AuthorizedPrincipal):
            raise AuthenticationFailed("authorizer returned an invalid principal")
        ensure_scope_authorized(principal, self._scope_code)
        ensure_purpose_authorized(principal, self._purpose_code)

        trace_reference: UUID = request.state.trace_reference
        correlation_reference = _parse_uuid_header(
            correlation_header,
            "X-Correlation-Id",
            default=trace_reference,
        )
        try:
            return PurposeContext(
                tenant_reference=principal.tenant_reference,
                actor_reference=principal.actor_reference,
                purpose_code=self._purpose_code,
                correlation_reference=correlation_reference,
                decision_reference=None,
                evidence_reference=None,
            )
        except ValueError as error:
            raise InvalidRequestMetadata from error


def get_people_repository(request: Request) -> PeopleRepository:
    """Return the repository injected when the application factory ran."""

    return request.app.state.repository


def create_app(
    repository: PeopleRepository,
    token_authorizer: TokenAuthorizer,
    *,
    maximum_body_bytes: int = 65_536,
    identifier_factory: IdentifierFactory = uuid4,
) -> FastAPI:
    """Create a dependency-injected API with no ambient production authority."""

    if not isinstance(repository, PeopleRepository):
        raise TypeError("repository must implement PeopleRepository")
    if not isinstance(token_authorizer, TokenAuthorizer):
        raise TypeError("token_authorizer must implement TokenAuthorizer")

    app = FastAPI(
        title="Orgmetra People API",
        summary="Purpose-bound people, candidate, and employment record operations.",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        license_info={
            "name": "Apache License 2.0",
            "identifier": "Apache-2.0",
        },
    )
    app.state.repository = repository
    app.state.token_authorizer = token_authorizer
    app.add_middleware(
        RequestBoundaryMiddleware,
        maximum_body_bytes=maximum_body_bytes,
        identifier_factory=identifier_factory,
    )
    register_exception_handlers(app)

    people_admin = RequiredPurpose("orgmetra.people.write", "people_admin")
    people_read = RequiredPurpose("orgmetra.people.read", "people_read")
    talent_acquisition = RequiredPurpose(
        "orgmetra.talent_acquisition.write",
        "talent_acquisition",
    )
    talent_read = RequiredPurpose(
        "orgmetra.talent_acquisition.read",
        "talent_acquisition_read",
    )
    audit_review = RequiredPurpose("orgmetra.audit.read", "audit_review")

    @app.get(
        "/health",
        response_model=HealthResponse,
        include_in_schema=False,
    )
    async def health() -> HealthResponse:
        """Return process liveness without claiming dependency readiness."""

        return HealthResponse(status="alive")

    @app.post(
        "/v1/people",
        response_model=PersonResponse,
        status_code=status.HTTP_201_CREATED,
        operation_id="createPersonRecord",
    )
    async def create_person(
        payload: PersonCreateRequest,
        context: PurposeContext = Depends(people_admin),
        repository_port: PeopleRepository = Depends(get_people_repository),
    ) -> PersonResponse:
        """Create one effective-dated person record idempotently."""

        snapshot = await run_in_threadpool(
            partial(
                repository_port.create_person,
                context,
                person_record_id=payload.person_record_id,
                display_name=payload.display_name,
                effective_from=payload.effective_from,
                effective_to=payload.effective_to,
            )
        )
        return PersonResponse.model_validate(snapshot)

    @app.get(
        "/v1/people/{person_record_id}",
        response_model=PersonResponse,
        operation_id="getPersonRecord",
    )
    async def get_person(
        person_record_id: UUID,
        context: PurposeContext = Depends(people_read),
        repository_port: PeopleRepository = Depends(get_people_repository),
    ) -> PersonResponse:
        """Return one current person record without cross-tenant disclosure."""

        snapshot = await run_in_threadpool(
            repository_port.get_person,
            context,
            person_record_id,
        )
        if snapshot is None:
            raise ResourceNotFound("person_record")
        return PersonResponse.model_validate(snapshot)

    @app.post(
        "/v1/employment-records",
        response_model=EmploymentResponse,
        status_code=status.HTTP_201_CREATED,
        operation_id="createEmploymentRecord",
    )
    async def create_employment(
        payload: EmploymentCreateRequest,
        context: PurposeContext = Depends(people_admin),
        repository_port: PeopleRepository = Depends(get_people_repository),
    ) -> EmploymentResponse:
        """Create one effective-dated employment relationship after hire."""

        snapshot = await run_in_threadpool(
            partial(
                repository_port.create_employment,
                context,
                employment_record_id=payload.employment_record_id,
                person_record_id=payload.person_record_id,
                employment_status_code=payload.employment_status_code,
                effective_from=payload.effective_from,
                effective_to=payload.effective_to,
            )
        )
        if snapshot is None:
            raise ResourceNotFound("person_record")
        return EmploymentResponse.model_validate(snapshot)

    @app.get(
        "/v1/employment-records/{employment_record_id}",
        response_model=EmploymentResponse,
        operation_id="getEmploymentRecord",
    )
    async def get_employment(
        employment_record_id: UUID,
        context: PurposeContext = Depends(people_read),
        repository_port: PeopleRepository = Depends(get_people_repository),
    ) -> EmploymentResponse:
        """Return one current employment record without cross-tenant disclosure."""

        snapshot = await run_in_threadpool(
            repository_port.get_employment,
            context,
            employment_record_id,
        )
        if snapshot is None:
            raise ResourceNotFound("employment_record")
        return EmploymentResponse.model_validate(snapshot)

    @app.post(
        "/v1/candidates",
        response_model=CandidateResponse,
        status_code=status.HTTP_201_CREATED,
        operation_id="createCandidateProfile",
    )
    async def create_candidate(
        payload: CandidateCreateRequest,
        context: PurposeContext = Depends(talent_acquisition),
        repository_port: PeopleRepository = Depends(get_people_repository),
    ) -> CandidateResponse:
        """Create one candidate profile under a talent-acquisition purpose."""

        snapshot = await run_in_threadpool(
            partial(
                repository_port.create_candidate,
                context,
                candidate_profile_id=payload.candidate_profile_id,
                application_status_code=payload.application_status_code,
            )
        )
        return CandidateResponse.model_validate(snapshot)

    @app.get(
        "/v1/candidates/{candidate_profile_id}",
        response_model=CandidateResponse,
        operation_id="getCandidateProfile",
    )
    async def get_candidate(
        candidate_profile_id: UUID,
        context: PurposeContext = Depends(talent_read),
        repository_port: PeopleRepository = Depends(get_people_repository),
    ) -> CandidateResponse:
        """Return one current candidate profile without cross-tenant disclosure."""

        snapshot = await run_in_threadpool(
            repository_port.get_candidate,
            context,
            candidate_profile_id,
        )
        if snapshot is None:
            raise ResourceNotFound("candidate_profile")
        return CandidateResponse.model_validate(snapshot)

    @app.post(
        "/v1/candidates/{candidate_profile_id}/worker-links",
        response_model=CandidateWorkerLinkResponse,
        status_code=status.HTTP_201_CREATED,
        operation_id="linkCandidateToWorker",
    )
    async def link_candidate_to_worker(
        candidate_profile_id: UUID,
        payload: CandidateWorkerLinkCreateRequest,
        context: PurposeContext = Depends(talent_acquisition),
        repository_port: PeopleRepository = Depends(get_people_repository),
    ) -> CandidateWorkerLinkResponse:
        """Append one immutable candidate-to-worker identity link."""

        link = await run_in_threadpool(
            partial(
                repository_port.link_candidate_to_worker,
                context,
                candidate_profile_id=candidate_profile_id,
                person_record_id=payload.person_record_id,
                candidate_worker_link_id=payload.candidate_worker_link_id,
            )
        )
        return CandidateWorkerLinkResponse.model_validate(link)

    @app.get(
        "/v1/candidates/{candidate_profile_id}/worker-links",
        response_model=CandidateWorkerLinkResponse,
        operation_id="getCandidateWorkerLink",
    )
    async def get_candidate_worker_link(
        candidate_profile_id: UUID,
        context: PurposeContext = Depends(talent_read),
        repository_port: PeopleRepository = Depends(get_people_repository),
    ) -> CandidateWorkerLinkResponse:
        """Return the hire link without disclosing an unauthorized candidate."""

        link = await run_in_threadpool(
            repository_port.get_candidate_worker_link,
            context,
            candidate_profile_id,
        )
        if link is None:
            raise ResourceNotFound("candidate_worker_link")
        return CandidateWorkerLinkResponse.model_validate(link)

    @app.get(
        "/v1/audit-events/{resource_record_id}",
        response_model=AuditEventListResponse,
        operation_id="listResourceAuditEvents",
    )
    async def list_audit_events(
        resource_record_id: UUID,
        context: PurposeContext = Depends(audit_review),
        repository_port: PeopleRepository = Depends(get_people_repository),
    ) -> AuditEventListResponse:
        """Return reference-only audit evidence visible to the audit purpose."""

        events = await run_in_threadpool(
            repository_port.list_audit_events,
            context,
            resource_record_id,
        )
        return AuditEventListResponse(
            audit_events=tuple(
                AuditEventResponse.model_validate(event) for event in events
            )
        )

    return app


def _parse_uuid_header(
    value: str | None,
    header_name: str,
    *,
    default: UUID | None,
) -> UUID | None:
    """Parse one optional UUID header without echoing the rejected value."""

    if value is None:
        return default
    try:
        return UUID(value.strip())
    except (AttributeError, ValueError) as error:
        raise InvalidRequestMetadata(
            f"{header_name} request metadata is invalid"
        ) from error
