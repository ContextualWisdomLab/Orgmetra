"""Deterministic test doubles for the Orgmetra people API."""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from orgmetra_people_api import AuthorizedPrincipal, create_app
from orgmetra_people_api.auth import AuthenticationFailed
from orgmetra_postgres import (
    AuditEvent,
    CandidateSnapshot,
    CandidateWorkerLink,
    PersonSnapshot,
    PurposeContext,
)


class FakeRepository:
    """Implement the people repository port without persistence."""

    def __init__(self) -> None:
        """Initialize deterministic projections and call evidence."""

        self.person: PersonSnapshot | None = None
        self.candidate: CandidateSnapshot | None = None
        self.worker_link: CandidateWorkerLink | None = None
        self.audit_events: tuple[AuditEvent, ...] = ()
        self.next_error: Exception | None = None
        self.last_context: PurposeContext | None = None
        self.last_call: tuple[str, tuple[object, ...], dict[str, object]] | None = None

    def _before(
        self,
        operation: str,
        context: PurposeContext,
        *args: object,
        **kwargs: object,
    ) -> None:
        """Record one call and raise a configured failure exactly once."""

        self.last_context = context
        self.last_call = (operation, args, kwargs)
        if self.next_error is not None:
            error = self.next_error
            self.next_error = None
            raise error

    def create_person(
        self,
        context: PurposeContext,
        *,
        person_record_id: UUID,
        display_name: str,
        effective_from: date,
        effective_to: date | None = None,
        recorded_at: datetime | None = None,
    ) -> PersonSnapshot:
        """Return an immutable person projection."""

        self._before(
            "create_person",
            context,
            person_record_id,
            display_name,
            effective_from,
            effective_to,
            recorded_at,
        )
        self.person = PersonSnapshot(
            person_record_id=person_record_id,
            display_name=display_name.strip(),
            effective_from=effective_from,
            effective_to=effective_to,
            recorded_from=recorded_at
            or datetime(2026, 8, 15, 9, 0, tzinfo=timezone.utc),
        )
        return self.person

    def get_person(
        self, context: PurposeContext, person_record_id: UUID
    ) -> PersonSnapshot | None:
        """Return the configured current person when identifiers match."""

        self._before("get_person", context, person_record_id)
        if self.person is None or self.person.person_record_id != person_record_id:
            return None
        return self.person

    def create_candidate(
        self,
        context: PurposeContext,
        *,
        candidate_profile_id: UUID,
        application_status_code: str,
    ) -> CandidateSnapshot:
        """Return an immutable candidate projection."""

        self._before(
            "create_candidate",
            context,
            candidate_profile_id,
            application_status_code,
        )
        self.candidate = CandidateSnapshot(
            candidate_profile_id=candidate_profile_id,
            application_status_code=application_status_code,
            recorded_at=datetime(2026, 8, 15, 9, 5, tzinfo=timezone.utc),
        )
        return self.candidate

    def link_candidate_to_worker(
        self,
        context: PurposeContext,
        *,
        candidate_profile_id: UUID,
        person_record_id: UUID,
        candidate_worker_link_id: UUID | None = None,
    ) -> CandidateWorkerLink:
        """Return an immutable candidate-to-worker projection."""

        self._before(
            "link_candidate_to_worker",
            context,
            candidate_profile_id,
            person_record_id,
            candidate_worker_link_id,
        )
        self.worker_link = CandidateWorkerLink(
            candidate_worker_link_id=candidate_worker_link_id or uuid4(),
            candidate_profile_id=candidate_profile_id,
            person_record_id=person_record_id,
            linked_at=datetime(2026, 8, 15, 9, 10, tzinfo=timezone.utc),
        )
        return self.worker_link

    def list_audit_events(
        self, context: PurposeContext, resource_record_id: UUID
    ) -> tuple[AuditEvent, ...]:
        """Return the configured reference-only audit evidence."""

        self._before("list_audit_events", context, resource_record_id)
        return self.audit_events


class FakeAuthorizer:
    """Authenticate one fixed bearer token and record requested purposes."""

    def __init__(self, principal: AuthorizedPrincipal) -> None:
        """Store the principal returned for valid test tokens."""

        self.principal = principal
        self.calls: list[tuple[str, str]] = []
        self.return_invalid_principal = False

    async def authorize(
        self, bearer_token: str, required_purpose_code: str
    ) -> AuthorizedPrincipal:
        """Return the configured principal or fail authentication."""

        self.calls.append((bearer_token, required_purpose_code))
        if bearer_token != "valid-token":
            raise AuthenticationFailed("invalid bearer token")
        if self.return_invalid_principal:
            return object()  # type: ignore[return-value]
        return self.principal


@pytest.fixture
def repository() -> FakeRepository:
    """Return a fresh in-memory repository double."""

    return FakeRepository()


@pytest.fixture
def authorizer() -> FakeAuthorizer:
    """Return a principal authorized for every implemented route purpose."""

    principal = AuthorizedPrincipal(
        tenant_reference=UUID("0198a412-6000-7000-8000-000000000001"),
        actor_reference=UUID("0198a412-6000-7000-8000-000000000002"),
        allowed_purpose_codes=frozenset(
            {"people_admin", "people_read", "talent_acquisition", "audit_review"}
        ),
    )
    return FakeAuthorizer(principal)


@pytest.fixture
def client(
    repository: FakeRepository,
    authorizer: FakeAuthorizer,
) -> TestClient:
    """Return a deterministic client with a fixed trace identifier."""

    app = create_app(
        repository,
        authorizer,
        identifier_factory=lambda: UUID(
            "0198a412-6000-7000-8000-000000000003"
        ),
    )
    return TestClient(app, raise_server_exceptions=False)
