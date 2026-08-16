"""Regression tests for client-safe support references."""

from __future__ import annotations

import re
from uuid import UUID

from fastapi.testclient import TestClient

from orgmetra_people_api import create_app

from conftest import FakeAuthorizer, FakeRepository


TRACE_REFERENCE = UUID("0198a412-6000-7000-8000-000000000077")
TENANT_REFERENCE = UUID("0198a412-6000-7000-8000-000000000078")
ACTOR_REFERENCE = UUID("0198a412-6000-7000-8000-000000000079")
SUPPORT_PATTERN = re.compile(r"^err_[A-Za-z0-9_-]{20,80}$")


def _client() -> TestClient:
    """Create a client whose internal trace identifier is known to the test."""

    from orgmetra_people_api import AuthorizedPrincipal

    principal = AuthorizedPrincipal(
        tenant_reference=TENANT_REFERENCE,
        actor_reference=ACTOR_REFERENCE,
        allowed_scope_codes=frozenset({"orgmetra.people.read"}),
        allowed_purpose_codes=frozenset({"people_read"}),
    )
    app = create_app(
        FakeRepository(),
        FakeAuthorizer(principal),
        identifier_factory=lambda: TRACE_REFERENCE,
    )
    return TestClient(app, raise_server_exceptions=False)


def _assert_safe_support_reference(response) -> str:
    """Require one opaque client reference independent of internal identity."""

    assert "x-request-id" not in response.headers
    support_reference = response.headers["x-support-reference"]
    assert SUPPORT_PATTERN.fullmatch(support_reference)
    assert support_reference not in {
        str(TRACE_REFERENCE),
        str(TENANT_REFERENCE),
        str(ACTOR_REFERENCE),
    }
    assert str(TRACE_REFERENCE) not in response.text
    assert str(TENANT_REFERENCE) not in response.text
    assert str(ACTOR_REFERENCE) not in response.text
    return support_reference


def test_normal_response_does_not_disclose_internal_trace() -> None:
    """Expose only a random support reference on successful responses."""

    response = _client().get("/health")

    assert response.status_code == 200
    _assert_safe_support_reference(response)


def test_handler_problem_uses_support_reference_and_next_action() -> None:
    """Use the client-safe reference in ordinary FastAPI error handling."""

    response = _client().get(
        "/v1/people/0198a412-6000-7000-8000-000000000080",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 404
    support_reference = _assert_safe_support_reference(response)
    document = response.json()
    assert document["support_reference"] == support_reference
    assert "trace_reference" not in document
    assert document["next_action"]


def test_predispatch_problem_uses_support_reference_and_next_action() -> None:
    """Keep malformed/oversized requests on the same non-leaking contract."""

    response = _client().post(
        "/v1/people",
        headers={"Content-Length": "70000"},
        content=b"",
    )

    assert response.status_code == 413
    support_reference = _assert_safe_support_reference(response)
    document = response.json()
    assert document["support_reference"] == support_reference
    assert "trace_reference" not in document
    assert document["next_action"]
