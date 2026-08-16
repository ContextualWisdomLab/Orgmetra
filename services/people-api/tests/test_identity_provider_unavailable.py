"""Regression tests for retryable identity-provider outages."""

from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient
from orgmetra_people_api import IdentityProviderUnavailable, create_app


class UnavailableAuthorizer:
    """Fail every authorization attempt at the external identity boundary."""

    async def authorize(
        self,
        bearer_token: str,
        required_scope_code: str,
        required_purpose_code: str,
    ) -> object:
        """Raise a retryable failure without exposing provider details."""

        assert bearer_token == "valid-token"
        assert required_scope_code == "orgmetra.people.read"
        assert required_purpose_code == "people_read"
        raise IdentityProviderUnavailable(
            "https://identity.internal.example/jwks timed out for tenant-secret"
        )


def test_identity_provider_outage_is_retryable_and_non_leaking(repository: object) -> None:
    """Map provider outages to a fixed 503 problem without endpoint leakage."""

    app = create_app(
        repository,  # type: ignore[arg-type]
        UnavailableAuthorizer(),
        identifier_factory=lambda: UUID(
            "0198a412-6000-7000-8000-000000000099"
        ),
    )
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get(
        "/v1/people/0198a412-6000-7000-8000-000000000010",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 503
    assert response.headers["Retry-After"] == "5"
    assert response.headers["Cache-Control"] == "no-store"
    payload = response.json()
    assert payload["error_code"] == "identity_provider_unavailable"
    assert payload["title"] == "Identity provider unavailable"
    assert payload["detail"] == "Authentication services are temporarily unavailable."
    assert "identity.internal.example" not in response.text
    assert "tenant-secret" not in response.text
