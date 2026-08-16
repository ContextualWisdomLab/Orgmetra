"""Unit tests for Keyverse verifier configuration and dependency contracts."""

from __future__ import annotations

from uuid import uuid4

import pytest

from orgmetra_keyverse_auth import (
    KeyverseOidcAuthorizer,
    KeyverseOidcConfig,
    ResolvedIdentityReferences,
)

from conftest import FakeIdentityResolver, FakeJwksProvider


def test_config_normalizes_valid_values() -> None:
    config = KeyverseOidcConfig(
        issuer="  https://identity.example.test/realm/orgmetra  ",
        audience="  orgmetra-api  ",
        tenant_claim_name=" tenant_claim ",
        purposes_claim_name=" purpose_claim ",
        allowed_algorithms=(" RS256 ", "ES256"),
        required_token_type=" at+jwt ",
        maximum_token_lifetime_seconds=600,
        clock_skew_seconds=0,
    )

    assert config.issuer == "https://identity.example.test/realm/orgmetra"
    assert config.audience == "orgmetra-api"
    assert config.tenant_claim_name == "tenant_claim"
    assert config.purposes_claim_name == "purpose_claim"
    assert config.allowed_algorithms == ("RS256", "ES256")
    assert config.required_token_type == "at+jwt"


@pytest.mark.parametrize(
    "issuer",
    [
        "http://identity.example.test",
        "https:///missing-host",
        "https://user@identity.example.test",
        "https://user:password@identity.example.test",
        "https://identity.example.test?query=yes",
        "https://identity.example.test#fragment",
        "https://identity.example.test\x1f",
    ],
)
def test_config_rejects_invalid_issuer(issuer: str) -> None:
    with pytest.raises(ValueError, match="issuer"):
        KeyverseOidcConfig(issuer=issuer, audience="orgmetra-api")


@pytest.mark.parametrize("audience", ["", "   ", "x" * 257, "api\x7fvalue"])
def test_config_rejects_invalid_audience(audience: str) -> None:
    with pytest.raises(ValueError, match="audience"):
        KeyverseOidcConfig(
            issuer="https://identity.example.test",
            audience=audience,
        )


@pytest.mark.parametrize(
    "field_name,value",
    [
        ("tenant_claim_name", ""),
        ("tenant_claim_name", "Tenant"),
        ("tenant_claim_name", "tenant-claim"),
        ("tenant_claim_name", "café"),
        ("tenant_claim_name", "x" * 65),
        ("tenant_claim_name", "tenant_claim\x1f"),
        ("purposes_claim_name", "Purpose"),
    ],
)
def test_config_rejects_invalid_claim_names(field_name: str, value: str) -> None:
    kwargs = {field_name: value}
    with pytest.raises(ValueError, match=field_name):
        KeyverseOidcConfig(
            issuer="https://identity.example.test",
            audience="orgmetra-api",
            **kwargs,
        )


@pytest.mark.parametrize(
    "algorithms",
    [(), ("RS256", "RS256"), ("HS256",), ("RS512",), ("RS256\x1f",)],
)
def test_config_rejects_empty_duplicate_or_unsupported_algorithms(
    algorithms: tuple[str, ...],
) -> None:
    with pytest.raises(ValueError, match="allowed_algorithms"):
        KeyverseOidcConfig(
            issuer="https://identity.example.test",
            audience="orgmetra-api",
            allowed_algorithms=algorithms,
        )


@pytest.mark.parametrize("token_type", ["", " ", "x" * 65, "at+jwt\x1f"])
def test_config_rejects_invalid_token_type(token_type: str) -> None:
    with pytest.raises(ValueError, match="required_token_type"):
        KeyverseOidcConfig(
            issuer="https://identity.example.test",
            audience="orgmetra-api",
            required_token_type=token_type,
        )


@pytest.mark.parametrize("lifetime", [59, 3_601])
def test_config_rejects_invalid_maximum_lifetime(lifetime: int) -> None:
    with pytest.raises(ValueError, match="maximum_token_lifetime_seconds"):
        KeyverseOidcConfig(
            issuer="https://identity.example.test",
            audience="orgmetra-api",
            maximum_token_lifetime_seconds=lifetime,
        )


@pytest.mark.parametrize("clock_skew", [-1, 121])
def test_config_rejects_invalid_clock_skew(clock_skew: int) -> None:
    with pytest.raises(ValueError, match="clock_skew_seconds"):
        KeyverseOidcConfig(
            issuer="https://identity.example.test",
            audience="orgmetra-api",
            clock_skew_seconds=clock_skew,
        )


def test_resolved_identity_references_are_immutable() -> None:
    references = ResolvedIdentityReferences(
        tenant_reference=uuid4(),
        actor_reference=uuid4(),
    )

    with pytest.raises(AttributeError):
        references.tenant_reference = uuid4()  # type: ignore[misc]


def test_authorizer_requires_both_dependency_ports() -> None:
    config = KeyverseOidcConfig(
        issuer="https://identity.example.test",
        audience="orgmetra-api",
    )
    provider = FakeJwksProvider({"keys": [{"kid": "key-1"}]})
    resolver = FakeIdentityResolver()

    with pytest.raises(TypeError, match="JwksProvider"):
        KeyverseOidcAuthorizer(config, object(), resolver)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="IdentityReferenceResolver"):
        KeyverseOidcAuthorizer(config, provider, object())  # type: ignore[arg-type]
