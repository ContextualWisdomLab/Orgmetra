"""Exercise defensive failures between authorization and repository context."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

import orgmetra_people_api.app as app_module
from orgmetra_people_api import create_app

from conftest import FakeAuthorizer, FakeRepository


AUTHORIZATION_HEADER = {"Authorization": "Bearer valid-token"}


def test_context_construction_failure_becomes_safe_metadata_problem(
    monkeypatch,
) -> None:
    """Refuse a context factory failure without invoking the repository."""

    from orgmetra_people_api import AuthorizedPrincipal

    repository = FakeRepository()
    authorizer = FakeAuthorizer(
        AuthorizedPrincipal(
            tenant_reference=uuid4(),
            actor_reference=uuid4(),
            allowed_scope_codes=frozenset({"orgmetra.people.read"}),
            allowed_purpose_codes=frozenset({"people_read"}),
        )
    )

    def invalid_context(**_kwargs: object) -> object:
        raise ValueError("sensitive context detail")

    monkeypatch.setattr(app_module, "PurposeContext", invalid_context)
    client = TestClient(
        create_app(repository, authorizer),
        raise_server_exceptions=False,
    )
    response = client.get(
        f"/v1/people/{uuid4()}",
        headers=AUTHORIZATION_HEADER,
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "invalid_request_metadata"
    assert "sensitive context detail" not in response.text
    assert repository.last_call is None
