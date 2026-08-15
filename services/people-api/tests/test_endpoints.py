"""End-to-end HTTP tests for the purpose-bound people API factory."""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from orgmetra_people_api import AuthorizedPrincipal, create_app
from orgmetra_postgres import (
    AuditEvent,
    RepositoryAuthorizationError,
    RepositoryConflictError,
    RepositoryUnavailableError,
)

from conftest import FakeAuthorizer, FakeRepository


AUTHORIZATION = {"Authorization": "Bearer valid-token"}


def _person_payload(person_record_id: UUID | None = None) -> dict[str, object]:
    """Return one valid person creation document."""

    return {
        "person_record_id": str(person_record_id or uuid4()),
        "display_name": "  Seongho Bae  ",
        "effective_from": "2026-08-15",
        "recorded_at": "2026-08-15T08:30:00Z",
    }


def test_health_is_public_and_security_headers_are_applied(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-request-id"] == (
        "0198a412-6000-7000-8000-000000000003"
    )


def test_openapi_exposes_stable_operations_and_bearer_scheme(client: TestClient) -> None:
    document = client.get("/openapi.json").json()

    assert document["info"]["version"] == "0.1.0"
    assert document["info"]["license"]["identifier"] == "Apache-2.0"
    assert set(document["paths"]) == {
        "/v1/people",
        "/v1/people/{person_record_id}",
        "/v1/candidates",
        "/v1/candidates/{candidate_profile_id}/worker-links",
        "/v1/audit-events/{resource_record_id}",
    }
    operation_ids = {
        operation["operationId"]
        for path in document["paths"].values()
        for operation in path.values()
    }
    assert operation_ids == {
        "createPersonRecord",
        "getPersonRecord",
        "createCandidateProfile",
        "linkCandidateToWorker",
        "listResourceAuditEvents",
    }
    assert document["components"]["securitySchemes"]["KeyverseBearer"] == {
        "type": "http",
        "scheme": "bearer",
    }
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404


def test_create_and_get_person_preserve_server_selected_context(
    client: TestClient,
    repository: FakeRepository,
    authorizer: FakeAuthorizer,
) -> None:
    person_id = uuid4()
    correlation_id = uuid4()
    decision_id = uuid4()
    headers = {
        **AUTHORIZATION,
        "X-Correlation-Id": str(correlation_id),
        "X-Decision-Reference": str(decision_id),
        "X-Evidence-Reference": " evidence://job-analysis/42 ",
    }

    created = client.post(
        "/v1/people",
        headers=headers,
        json=_person_payload(person_id),
    )

    assert created.status_code == 201
    assert created.json() == {
        "person_record_id": str(person_id),
        "display_name": "Seongho Bae",
        "effective_from": "2026-08-15",
        "effective_to": None,
        "recorded_from": "2026-08-15T08:30:00Z",
    }
    assert authorizer.calls[-1] == ("valid-token", "people_admin")
    assert repository.last_context is not None
    assert repository.last_context.tenant_reference == authorizer.principal.tenant_reference
    assert repository.last_context.actor_reference == authorizer.principal.actor_reference
    assert repository.last_context.purpose_code == "people_admin"
    assert repository.last_context.correlation_reference == correlation_id
    assert repository.last_context.decision_reference == decision_id
    assert repository.last_context.evidence_reference == "evidence://job-analysis/42"

    fetched = client.get(
        f"/v1/people/{person_id}",
        headers=AUTHORIZATION,
    )
    assert fetched.status_code == 200
    assert fetched.json() == created.json()
    assert authorizer.calls[-1] == ("valid-token", "people_read")
    assert repository.last_context is not None
    assert repository.last_context.correlation_reference == UUID(
        "0198a412-6000-7000-8000-000000000003"
    )


def test_candidate_link_and_audit_workflow(
    client: TestClient,
    repository: FakeRepository,
) -> None:
    candidate_id = uuid4()
    person_id = uuid4()
    link_id = uuid4()

    candidate = client.post(
        "/v1/candidates",
        headers=AUTHORIZATION,
        json={
            "candidate_profile_id": str(candidate_id),
            "application_status_code": "structured_screen",
        },
    )
    assert candidate.status_code == 201
    assert candidate.json()["candidate_profile_id"] == str(candidate_id)
    assert candidate.json()["application_status_code"] == "structured_screen"

    linked = client.post(
        f"/v1/candidates/{candidate_id}/worker-links",
        headers=AUTHORIZATION,
        json={
            "person_record_id": str(person_id),
            "candidate_worker_link_id": str(link_id),
        },
    )
    assert linked.status_code == 201
    assert linked.json() == {
        "candidate_worker_link_id": str(link_id),
        "candidate_profile_id": str(candidate_id),
        "person_record_id": str(person_id),
        "linked_at": "2026-08-15T09:10:00Z",
    }

    event_id = uuid4()
    repository.audit_events = (
        AuditEvent(
            audit_event_id=event_id,
            action_code="candidate_worker_linked",
            resource_type_code="candidate_worker_link",
            resource_record_id=link_id,
            actor_reference=uuid4(),
            purpose_code="talent_acquisition",
            occurred_at=datetime(2026, 8, 15, 9, 11, tzinfo=timezone.utc),
        ),
    )
    audited = client.get(
        f"/v1/audit-events/{link_id}",
        headers=AUTHORIZATION,
    )
    assert audited.status_code == 200
    assert audited.json()["audit_events"][0]["audit_event_id"] == str(event_id)
    assert "display_name" not in audited.text
    assert "assessment_response" not in audited.text


def test_absent_person_returns_uniform_not_found(
    client: TestClient,
) -> None:
    response = client.get(f"/v1/people/{uuid4()}", headers=AUTHORIZATION)

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["error_code"] == "resource_not_found"
    assert "not visible" in response.json()["detail"]


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Basic credential"},
        {"Authorization": "Bearer invalid-token"},
    ],
)
def test_authentication_failures_are_fixed_and_non_leaking(
    client: TestClient,
    headers: dict[str, str],
) -> None:
    response = client.get(f"/v1/people/{uuid4()}", headers=headers)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["error_code"] == "authentication_failed"
    assert "invalid-token" not in response.text
    assert "credential" not in response.text


def test_authorizer_cannot_return_an_insufficient_principal(
    repository: FakeRepository,
) -> None:
    principal = AuthorizedPrincipal(
        tenant_reference=uuid4(),
        actor_reference=uuid4(),
        allowed_purpose_codes=frozenset({"people_read"}),
    )
    client = TestClient(
        create_app(repository, FakeAuthorizer(principal)),
        raise_server_exceptions=False,
    )

    response = client.post(
        "/v1/people",
        headers=AUTHORIZATION,
        json=_person_payload(),
    )
    assert response.status_code == 403
    assert response.json()["error_code"] == "purpose_not_authorized"


def test_invalid_principal_fails_as_authentication_error(
    client: TestClient,
    authorizer: FakeAuthorizer,
) -> None:
    authorizer.return_invalid_principal = True

    response = client.get(f"/v1/people/{uuid4()}", headers=AUTHORIZATION)
    assert response.status_code == 401
    assert response.json()["error_code"] == "authentication_failed"


@pytest.mark.parametrize(
    "header_name,header_value",
    [
        ("X-Correlation-Id", "not-a-uuid"),
        ("X-Decision-Reference", "not-a-uuid"),
        ("X-Evidence-Reference", "   "),
        ("X-Evidence-Reference", "x" * 513),
    ],
)
def test_invalid_request_metadata_is_rejected(
    client: TestClient,
    header_name: str,
    header_value: str,
) -> None:
    response = client.post(
        "/v1/people",
        headers={**AUTHORIZATION, header_name: header_value},
        json=_person_payload(),
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "invalid_request_metadata"
    assert header_value.strip() not in response.text


def test_validation_errors_do_not_echo_rejected_hr_content(client: TestClient) -> None:
    response = client.post(
        "/v1/people",
        headers=AUTHORIZATION,
        json={
            "person_record_id": str(uuid4()),
            "display_name": "VERY_SECRET_PERSON_NAME",
            "effective_from": "2026-08-15",
            "effective_to": "2026-08-15",
            "unknown_field": "SHOULD_NOT_ECHO",
        },
    )

    assert response.status_code == 422
    document = response.json()
    assert document["error_code"] == "request_validation_failed"
    assert document["invalid_fields"]
    assert "VERY_SECRET_PERSON_NAME" not in response.text
    assert "SHOULD_NOT_ECHO" not in response.text


@pytest.mark.parametrize(
    "error,status_code,error_code",
    [
        (RepositoryAuthorizationError("sensitive"), 403, "repository_access_denied"),
        (RepositoryConflictError("existing name"), 409, "immutable_identity_conflict"),
        (RepositoryUnavailableError("postgresql://secret"), 503, "repository_unavailable"),
        (RuntimeError("internal PII"), 500, "internal_error"),
    ],
)
def test_repository_and_unexpected_errors_are_safely_translated(
    client: TestClient,
    repository: FakeRepository,
    error: Exception,
    status_code: int,
    error_code: str,
) -> None:
    repository.next_error = error

    response = client.get(f"/v1/people/{uuid4()}", headers=AUTHORIZATION)
    assert response.status_code == status_code
    assert response.json()["error_code"] == error_code
    assert str(error) not in response.text
    if status_code == 503:
        assert response.headers["retry-after"] == "5"
