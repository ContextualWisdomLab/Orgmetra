"""Fail-closed JOSE header and JWK Set verification tests."""

from __future__ import annotations

import asyncio

import pytest

from orgmetra_keyverse_auth import KeyverseOidcAuthorizer, KeyverseOidcConfig
from orgmetra_people_api import AuthenticationFailed, IdentityProviderUnavailable

from conftest import (
    FakeIdentityResolver,
    FakeJwksProvider,
    KeyMaterial,
    encode_token,
)


def _authorizer(config, provider, resolver) -> KeyverseOidcAuthorizer:
    """Create one authorizer for focused hostile-input tests."""

    return KeyverseOidcAuthorizer(config, provider, resolver)


@pytest.mark.parametrize(
    "token",
    [
        "",
        "no-dots",
        "one.dot",
        "a.b.c.d",
        "é.a.b",
        "a. b.c",
        "x" * 8193 + ".a.b",
        123,
    ],
)
def test_compact_token_surface_rejects_malformed_values(
    token: object,
    oidc_config,
    jwks_provider,
    identity_resolver,
) -> None:
    authorizer = _authorizer(oidc_config, jwks_provider, identity_resolver)

    with pytest.raises(AuthenticationFailed, match="bearer token"):
        asyncio.run(authorizer.authorize(token, "people_read"))  # type: ignore[arg-type]


def test_invalid_compact_header_is_rejected(
    oidc_config,
    jwks_provider,
    identity_resolver,
) -> None:
    authorizer = _authorizer(oidc_config, jwks_provider, identity_resolver)

    with pytest.raises(AuthenticationFailed, match="header"):
        asyncio.run(authorizer.authorize("not-json.payload.signature", "people_read"))


@pytest.mark.parametrize(
    "header_overrides,error_fragment",
    [
        ({"typ": None}, "typ"),
        ({"typ": "JWT"}, "type"),
        ({"typ": "x" * 65}, "typ"),
        ({"typ": "at+jwt\x7f"}, "typ"),
        ({"kid": None}, "kid"),
        ({"kid": "x" * 257}, "kid"),
        ({"kid": "key\x7f"}, "kid"),
    ],
)
def test_required_header_fields_are_strict(
    key_material: KeyMaterial,
    oidc_config,
    jwks_provider,
    identity_resolver,
    header_overrides: dict[str, object],
    error_fragment: str,
) -> None:
    token = encode_token(
        key_material,
        oidc_config,
        header_overrides=header_overrides,
    )
    authorizer = _authorizer(oidc_config, jwks_provider, identity_resolver)

    with pytest.raises(AuthenticationFailed, match=error_fragment):
        asyncio.run(authorizer.authorize(token, "people_read"))


def test_symmetric_algorithm_is_rejected_before_key_selection(
    key_material: KeyMaterial,
    oidc_config,
    jwks_provider,
    identity_resolver,
) -> None:
    token = encode_token(
        key_material,
        oidc_config,
        algorithm="HS256",
        signing_key="not-a-production-secret",
    )
    authorizer = _authorizer(oidc_config, jwks_provider, identity_resolver)

    with pytest.raises(AuthenticationFailed, match="algorithm"):
        asyncio.run(authorizer.authorize(token, "people_read"))


@pytest.mark.parametrize(
    "document",
    [
        object(),
        {},
        {"keys": "not-a-list"},
        {"keys": []},
        {"keys": [{}] * 129},
        {"keys": ["not-a-jwk"]},
    ],
)
def test_invalid_jwk_set_is_provider_unavailable(
    key_material: KeyMaterial,
    oidc_config,
    identity_resolver,
    document: object,
) -> None:
    provider = FakeJwksProvider(document)  # type: ignore[arg-type]
    authorizer = _authorizer(oidc_config, provider, identity_resolver)
    token = encode_token(key_material, oidc_config)

    with pytest.raises(IdentityProviderUnavailable, match="key set"):
        asyncio.run(authorizer.authorize(token, "people_read"))


@pytest.mark.parametrize(
    "mutator",
    [
        lambda jwk: jwk.update({"kid": "other-key"}),
        lambda jwk: jwk.update({"use": "enc"}),
        lambda jwk: jwk.update({"alg": "PS256"}),
    ],
)
def test_unaccepted_signing_key_is_authentication_failure(
    key_material: KeyMaterial,
    oidc_config,
    identity_resolver,
    mutator,
) -> None:
    jwk = dict(key_material.public_jwk)
    mutator(jwk)
    provider = FakeJwksProvider({"keys": [jwk]})
    authorizer = _authorizer(oidc_config, provider, identity_resolver)
    token = encode_token(key_material, oidc_config)

    with pytest.raises(AuthenticationFailed, match="signing key"):
        asyncio.run(authorizer.authorize(token, "people_read"))


def test_duplicate_matching_key_is_provider_failure(
    key_material: KeyMaterial,
    oidc_config,
    identity_resolver,
) -> None:
    provider = FakeJwksProvider(
        {"keys": [dict(key_material.public_jwk), dict(key_material.public_jwk)]}
    )
    authorizer = _authorizer(oidc_config, provider, identity_resolver)
    token = encode_token(key_material, oidc_config)

    with pytest.raises(IdentityProviderUnavailable, match="ambiguous"):
        asyncio.run(authorizer.authorize(token, "people_read"))


def test_malformed_matching_jwk_is_provider_failure(
    key_material: KeyMaterial,
    oidc_config,
    identity_resolver,
) -> None:
    provider = FakeJwksProvider(
        {
            "keys": [
                {
                    "kid": "key-1",
                    "alg": "RS256",
                    "use": "sig",
                    "kty": "RSA",
                    "n": "not-valid-base64url!",
                    "e": "AQAB",
                }
            ]
        }
    )
    authorizer = _authorizer(oidc_config, provider, identity_resolver)
    token = encode_token(key_material, oidc_config)

    with pytest.raises(IdentityProviderUnavailable, match="signing key"):
        asyncio.run(authorizer.authorize(token, "people_read"))


def test_jwk_derived_algorithm_must_match_header(
    key_material: KeyMaterial,
    identity_resolver: FakeIdentityResolver,
) -> None:
    config = KeyverseOidcConfig(
        issuer="https://identity.example.test/realms/orgmetra",
        audience="orgmetra-people-api",
        allowed_algorithms=("PS256",),
    )
    jwk = dict(key_material.public_jwk)
    jwk.pop("alg")
    provider = FakeJwksProvider({"keys": [jwk]})
    authorizer = _authorizer(config, provider, identity_resolver)
    token = encode_token(
        key_material,
        config,
        algorithm="PS256",
    )

    with pytest.raises(AuthenticationFailed, match="algorithm does not match"):
        asyncio.run(authorizer.authorize(token, "people_read"))
