"""Successful verification tests for the Keyverse OIDC authorizer."""

from __future__ import annotations

import asyncio

from orgmetra_keyverse_auth import KeyverseOidcAuthorizer

from conftest import (
    FakeIdentityResolver,
    FakeJwksProvider,
    KeyMaterial,
    encode_token,
)


def test_valid_token_resolves_orgmetra_principal(
    key_material: KeyMaterial,
    oidc_config,
    jwks_provider: FakeJwksProvider,
    identity_resolver: FakeIdentityResolver,
) -> None:
    authorizer = KeyverseOidcAuthorizer(
        oidc_config,
        jwks_provider,
        identity_resolver,
    )
    token = encode_token(key_material, oidc_config)

    principal = asyncio.run(
        authorizer.authorize(
            token,
            " orgmetra.people.read ",
            " people_read ",
        )
    )

    assert principal.tenant_reference == identity_resolver.references.tenant_reference
    assert principal.actor_reference == identity_resolver.references.actor_reference
    assert principal.allowed_scope_codes == frozenset(
        {"orgmetra.people.read", "orgmetra.people.write"}
    )
    assert principal.allowed_purpose_codes == frozenset(
        {"people_read", "people_admin"}
    )
    assert jwks_provider.calls == [oidc_config.issuer]
    assert identity_resolver.calls == [
        (oidc_config.issuer, "keyverse-subject-1", "customer-1")
    ]


def test_header_type_is_case_insensitive_and_optional_jwk_metadata_defaults(
    key_material: KeyMaterial,
    oidc_config,
    identity_resolver: FakeIdentityResolver,
) -> None:
    jwk = dict(key_material.public_jwk)
    jwk.pop("use")
    jwk.pop("alg")
    provider = FakeJwksProvider({"keys": [jwk]})
    authorizer = KeyverseOidcAuthorizer(
        oidc_config,
        provider,
        identity_resolver,
    )
    token = encode_token(
        key_material,
        oidc_config,
        header_overrides={"typ": "AT+JWT"},
    )

    principal = asyncio.run(
        authorizer.authorize(token, "orgmetra.people.write", "people_admin")
    )

    assert "orgmetra.people.write" in principal.allowed_scope_codes
    assert "people_admin" in principal.allowed_purpose_codes
