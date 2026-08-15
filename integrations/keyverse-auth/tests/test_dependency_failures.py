"""Dependency-failure tests for the offline Keyverse authorization adapter."""

from __future__ import annotations

import asyncio

import pytest

from orgmetra_keyverse_auth import KeyverseOidcAuthorizer
from orgmetra_people_api import IdentityProviderUnavailable

from conftest import (
    FakeIdentityResolver,
    FakeJwksProvider,
    KeyMaterial,
    encode_token,
)


def _authorizer(config, provider, resolver) -> KeyverseOidcAuthorizer:
    """Create one authorizer for dependency-boundary tests."""

    return KeyverseOidcAuthorizer(config, provider, resolver)


def test_provider_owned_unavailability_is_preserved(
    key_material: KeyMaterial,
    oidc_config,
    jwks_provider: FakeJwksProvider,
    identity_resolver: FakeIdentityResolver,
) -> None:
    jwks_provider.error = IdentityProviderUnavailable("provider unavailable")
    authorizer = _authorizer(oidc_config, jwks_provider, identity_resolver)

    with pytest.raises(IdentityProviderUnavailable, match="provider unavailable"):
        asyncio.run(
            authorizer.authorize(
                encode_token(key_material, oidc_config),
                "people_read",
            )
        )
    assert identity_resolver.calls == []


def test_unexpected_provider_error_is_translated_without_detail(
    key_material: KeyMaterial,
    oidc_config,
    jwks_provider: FakeJwksProvider,
    identity_resolver: FakeIdentityResolver,
) -> None:
    jwks_provider.error = RuntimeError("https://secret.internal/jwks")
    authorizer = _authorizer(oidc_config, jwks_provider, identity_resolver)

    with pytest.raises(
        IdentityProviderUnavailable,
        match="signing keys are temporarily unavailable",
    ) as captured:
        asyncio.run(
            authorizer.authorize(
                encode_token(key_material, oidc_config),
                "people_read",
            )
        )
    assert "secret.internal" not in str(captured.value)
    assert identity_resolver.calls == []


def test_resolver_owned_unavailability_is_preserved(
    key_material: KeyMaterial,
    oidc_config,
    jwks_provider: FakeJwksProvider,
    identity_resolver: FakeIdentityResolver,
) -> None:
    identity_resolver.error = IdentityProviderUnavailable("mapping unavailable")
    authorizer = _authorizer(oidc_config, jwks_provider, identity_resolver)

    with pytest.raises(IdentityProviderUnavailable, match="mapping unavailable"):
        asyncio.run(
            authorizer.authorize(
                encode_token(key_material, oidc_config),
                "people_read",
            )
        )


def test_unexpected_resolver_error_is_translated_without_identity_detail(
    key_material: KeyMaterial,
    oidc_config,
    jwks_provider: FakeJwksProvider,
    identity_resolver: FakeIdentityResolver,
) -> None:
    identity_resolver.error = RuntimeError("customer-1/keyverse-subject-1")
    authorizer = _authorizer(oidc_config, jwks_provider, identity_resolver)

    with pytest.raises(
        IdentityProviderUnavailable,
        match="mapping is temporarily unavailable",
    ) as captured:
        asyncio.run(
            authorizer.authorize(
                encode_token(key_material, oidc_config),
                "people_read",
            )
        )
    assert "customer-1" not in str(captured.value)
    assert "keyverse-subject-1" not in str(captured.value)


def test_invalid_resolver_result_is_provider_failure(
    key_material: KeyMaterial,
    oidc_config,
    jwks_provider: FakeJwksProvider,
    identity_resolver: FakeIdentityResolver,
) -> None:
    identity_resolver.return_invalid_result = True
    authorizer = _authorizer(oidc_config, jwks_provider, identity_resolver)

    with pytest.raises(
        IdentityProviderUnavailable,
        match="reference mapping is invalid",
    ):
        asyncio.run(
            authorizer.authorize(
                encode_token(key_material, oidc_config),
                "people_read",
            )
        )
