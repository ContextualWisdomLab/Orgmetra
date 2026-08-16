"""Independent OAuth scope and HR-purpose authorization tests."""

from __future__ import annotations

import asyncio

import pytest

from orgmetra_keyverse_auth import KeyverseOidcAuthorizer
from orgmetra_people_api import AuthenticationFailed, AuthorizationDenied

from conftest import (
    FakeIdentityResolver,
    FakeJwksProvider,
    KeyMaterial,
    encode_token,
)


def _authorizer(config, provider, resolver) -> KeyverseOidcAuthorizer:
    """Create one strict authorizer for operation-scope tests."""

    return KeyverseOidcAuthorizer(config, provider, resolver)


def test_scope_and_purpose_are_independently_required(
    key_material: KeyMaterial,
    oidc_config,
    jwks_provider: FakeJwksProvider,
    identity_resolver: FakeIdentityResolver,
) -> None:
    """Return both validated grants only when route scope and purpose are present."""

    token = encode_token(
        key_material,
        oidc_config,
        payload_overrides={
            "scope": "orgmetra.people.read orgmetra.people.write",
            oidc_config.purposes_claim_name: ["people_read", "people_admin"],
        },
    )
    authorizer = _authorizer(oidc_config, jwks_provider, identity_resolver)

    principal = asyncio.run(
        authorizer.authorize(token, "orgmetra.people.write", "people_admin")
    )

    assert principal.allowed_scope_codes == frozenset(
        {"orgmetra.people.read", "orgmetra.people.write"}
    )
    assert principal.allowed_purpose_codes == frozenset(
        {"people_read", "people_admin"}
    )


def test_business_purpose_cannot_enlarge_missing_operation_scope(
    key_material: KeyMaterial,
    oidc_config,
    jwks_provider: FakeJwksProvider,
    identity_resolver: FakeIdentityResolver,
) -> None:
    """Deny a valid HR purpose when the token lacks the route capability."""

    token = encode_token(
        key_material,
        oidc_config,
        payload_overrides={
            "scope": "orgmetra.people.read",
            oidc_config.purposes_claim_name: ["people_admin"],
        },
    )
    authorizer = _authorizer(oidc_config, jwks_provider, identity_resolver)

    with pytest.raises(AuthorizationDenied, match="scope"):
        asyncio.run(
            authorizer.authorize(token, "orgmetra.people.write", "people_admin")
        )
    assert identity_resolver.calls == []


@pytest.mark.parametrize(
    "scope_claim",
    [
        None,
        "",
        "orgmetra.people.read orgmetra.people.read",
        "orgmetra.people.READ",
        "orgmetra.people.read café",
        " ".join(f"orgmetra.people.scope{index}" for index in range(65)),
        "x" * 129,
        ["orgmetra.people.read"],
    ],
)
def test_scope_claim_is_bounded_ascii_and_duplicate_free(
    key_material: KeyMaterial,
    oidc_config,
    jwks_provider: FakeJwksProvider,
    identity_resolver: FakeIdentityResolver,
    scope_claim: object,
) -> None:
    """Reject malformed or ambiguous RFC 9068 scope claims before identity mapping."""

    token = encode_token(
        key_material,
        oidc_config,
        payload_overrides={"scope": scope_claim},
    )
    authorizer = _authorizer(oidc_config, jwks_provider, identity_resolver)

    with pytest.raises(AuthenticationFailed, match="scope"):
        asyncio.run(
            authorizer.authorize(token, "orgmetra.people.read", "people_read")
        )
    assert identity_resolver.calls == []


@pytest.mark.parametrize(
    "required_scope",
    ["", "ORGmetra.people.read", "orgmetra/people/read", "café", "x" * 129],
)
def test_invalid_route_scope_fails_before_key_provider_access(
    key_material: KeyMaterial,
    oidc_config,
    jwks_provider: FakeJwksProvider,
    identity_resolver: FakeIdentityResolver,
    required_scope: str,
) -> None:
    """Reject an invalid server-selected scope before consulting dependencies."""

    token = encode_token(
        key_material,
        oidc_config,
        payload_overrides={"scope": "orgmetra.people.read"},
    )
    authorizer = _authorizer(oidc_config, jwks_provider, identity_resolver)

    with pytest.raises(AuthenticationFailed, match="scope code"):
        asyncio.run(authorizer.authorize(token, required_scope, "people_read"))
    assert jwks_provider.calls == []
    assert identity_resolver.calls == []
