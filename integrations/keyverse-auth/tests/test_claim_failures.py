"""Fail-closed registered, identity, scope, and purpose claim verification tests."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Mapping

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from orgmetra_keyverse_auth import KeyverseOidcAuthorizer
from orgmetra_people_api import AuthenticationFailed, AuthorizationDenied

from conftest import (
    FakeIdentityResolver,
    FakeJwksProvider,
    KeyMaterial,
    encode_token,
)

_READ_SCOPE = "orgmetra.people.read"
_WRITE_SCOPE = "orgmetra.people.write"


def _authorizer(config, provider, resolver) -> KeyverseOidcAuthorizer:
    """Create one strict authorizer for hostile-claim tests."""

    return KeyverseOidcAuthorizer(config, provider, resolver)


def _token_without_claim(
    key_material: KeyMaterial,
    oidc_config,
    claim_name: str,
) -> str:
    """Create a validly signed token with one mandatory claim omitted."""

    source = encode_token(key_material, oidc_config)
    payload = jwt.decode(source, options={"verify_signature": False})
    del payload[claim_name]
    return jwt.encode(
        payload,
        key_material.private_key,
        algorithm="RS256",
        headers={"kid": "key-1", "typ": "at+jwt"},
    )


def test_invalid_signature_is_rejected(
    key_material: KeyMaterial,
    oidc_config,
    jwks_provider,
    identity_resolver,
) -> None:
    other_key = rsa.generate_private_key(public_exponent=65_537, key_size=2_048)
    token = encode_token(
        key_material,
        oidc_config,
        signing_key=other_key,
    )
    authorizer = _authorizer(oidc_config, jwks_provider, identity_resolver)

    with pytest.raises(AuthenticationFailed, match="signature or claims"):
        asyncio.run(authorizer.authorize(token, _READ_SCOPE, "people_read"))


@pytest.mark.parametrize(
    "payload_overrides",
    [
        {"iss": "https://wrong.example.test"},
        {"aud": "wrong-audience"},
        {"exp": int(time.time()) - 300},
        {"iat": int(time.time()) + 300},
        {"nbf": int(time.time()) + 300},
    ],
)
def test_invalid_registered_claims_are_rejected(
    key_material: KeyMaterial,
    oidc_config,
    jwks_provider,
    identity_resolver,
    payload_overrides: Mapping[str, object],
) -> None:
    token = encode_token(
        key_material,
        oidc_config,
        payload_overrides=payload_overrides,
    )
    authorizer = _authorizer(oidc_config, jwks_provider, identity_resolver)

    with pytest.raises(AuthenticationFailed, match="signature or claims"):
        asyncio.run(authorizer.authorize(token, _READ_SCOPE, "people_read"))


@pytest.mark.parametrize("claim_name", ["iss", "sub", "aud", "exp", "iat", "jti"])
def test_missing_mandatory_registered_claim_is_rejected(
    key_material: KeyMaterial,
    oidc_config,
    jwks_provider,
    identity_resolver,
    claim_name: str,
) -> None:
    token = _token_without_claim(key_material, oidc_config, claim_name)
    authorizer = _authorizer(oidc_config, jwks_provider, identity_resolver)

    with pytest.raises(AuthenticationFailed, match="signature or claims"):
        asyncio.run(authorizer.authorize(token, _READ_SCOPE, "people_read"))


@pytest.mark.parametrize(
    "claim_name,value",
    [
        ("sub", ""),
        ("sub", "x" * 256),
        ("sub", "subject\x7f"),
        ("jti", 123),
        ("jti", " "),
        ("jti", "x" * 256),
        ("jti", "token\x1f"),
        ("orgmetra_tenant", []),
        ("orgmetra_tenant", ""),
        ("orgmetra_tenant", "x" * 256),
        ("orgmetra_tenant", "tenant\x7f"),
    ],
)
def test_identity_claims_are_required_bounded_strings(
    key_material: KeyMaterial,
    oidc_config,
    jwks_provider,
    identity_resolver,
    claim_name: str,
    value: object,
) -> None:
    token = encode_token(
        key_material,
        oidc_config,
        payload_overrides={claim_name: value},
    )
    authorizer = _authorizer(oidc_config, jwks_provider, identity_resolver)

    with pytest.raises(AuthenticationFailed, match="claim is invalid"):
        asyncio.run(authorizer.authorize(token, _READ_SCOPE, "people_read"))


def test_token_lifetime_must_be_positive_after_clock_skew(
    key_material: KeyMaterial,
    oidc_config,
    jwks_provider,
    identity_resolver,
) -> None:
    now = int(time.time())
    token = encode_token(
        key_material,
        oidc_config,
        payload_overrides={"iat": now + 10, "exp": now + 5},
    )
    authorizer = _authorizer(oidc_config, jwks_provider, identity_resolver)

    with pytest.raises(AuthenticationFailed, match="lifetime is invalid"):
        asyncio.run(authorizer.authorize(token, _READ_SCOPE, "people_read"))


def test_token_lifetime_cannot_exceed_configured_maximum(
    key_material: KeyMaterial,
    oidc_config,
    jwks_provider,
    identity_resolver,
) -> None:
    now = int(time.time())
    token = encode_token(
        key_material,
        oidc_config,
        payload_overrides={"iat": now - 5, "exp": now + 901},
    )
    authorizer = _authorizer(oidc_config, jwks_provider, identity_resolver)

    with pytest.raises(AuthenticationFailed, match="allowed maximum"):
        asyncio.run(authorizer.authorize(token, _READ_SCOPE, "people_read"))


@pytest.mark.parametrize(
    "purposes",
    [
        "people_read",
        [],
        ["purpose"] * 65,
        [123],
        [""],
        ["UPPER"],
        ["people-read"],
        ["café"],
        ["x" * 129],
        ["people_read", "people_read"],
    ],
)
def test_purpose_collection_is_bounded_and_duplicate_free(
    key_material: KeyMaterial,
    oidc_config,
    jwks_provider,
    identity_resolver,
    purposes: object,
) -> None:
    token = encode_token(
        key_material,
        oidc_config,
        payload_overrides={oidc_config.purposes_claim_name: purposes},
    )
    authorizer = _authorizer(oidc_config, jwks_provider, identity_resolver)

    with pytest.raises(AuthenticationFailed, match="purpose"):
        asyncio.run(authorizer.authorize(token, _READ_SCOPE, "people_read"))


def test_token_without_required_route_purpose_is_denied(
    key_material: KeyMaterial,
    oidc_config,
    jwks_provider,
    identity_resolver,
) -> None:
    token = encode_token(
        key_material,
        oidc_config,
        payload_overrides={
            oidc_config.purposes_claim_name: ["people_read"],
        },
    )
    authorizer = _authorizer(oidc_config, jwks_provider, identity_resolver)

    with pytest.raises(AuthorizationDenied, match="purpose"):
        asyncio.run(authorizer.authorize(token, _WRITE_SCOPE, "people_admin"))


@pytest.mark.parametrize("purpose", ["", "UPPER", "people-read", "café", "x" * 129])
def test_invalid_route_purpose_fails_before_key_provider_access(
    key_material: KeyMaterial,
    oidc_config,
    jwks_provider: FakeJwksProvider,
    identity_resolver: FakeIdentityResolver,
    purpose: str,
) -> None:
    token = encode_token(key_material, oidc_config)
    authorizer = _authorizer(oidc_config, jwks_provider, identity_resolver)

    with pytest.raises(AuthenticationFailed, match="purpose code"):
        asyncio.run(authorizer.authorize(token, _READ_SCOPE, purpose))
    assert jwks_provider.calls == []
    assert identity_resolver.calls == []
