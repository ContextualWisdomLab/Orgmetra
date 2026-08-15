"""Deterministic test fixtures for the Keyverse JWT authorizer."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Mapping
from uuid import UUID

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from orgmetra_keyverse_auth import (
    KeyverseOidcConfig,
    ResolvedIdentityReferences,
)


@dataclass(frozen=True, slots=True)
class KeyMaterial:
    """Hold one test signing key and its public JWK."""

    private_key: rsa.RSAPrivateKey
    public_jwk: dict[str, object]


class FakeJwksProvider:
    """Return one configurable issuer-specific JWK Set."""

    def __init__(self, document: Mapping[str, object]) -> None:
        """Store the key document and initialize call evidence."""

        self.document = document
        self.error: Exception | None = None
        self.calls: list[str] = []

    async def get_jwks(self, issuer: str) -> Mapping[str, object]:
        """Return the configured key set or raise one configured failure."""

        self.calls.append(issuer)
        if self.error is not None:
            raise self.error
        return self.document


class FakeIdentityResolver:
    """Map one external identity pair to deterministic Orgmetra references."""

    def __init__(self) -> None:
        """Initialize stable references and call evidence."""

        self.references = ResolvedIdentityReferences(
            tenant_reference=UUID("0198a412-6000-7000-8000-000000000101"),
            actor_reference=UUID("0198a412-6000-7000-8000-000000000102"),
        )
        self.error: Exception | None = None
        self.return_invalid_result = False
        self.calls: list[tuple[str, str, str]] = []

    async def resolve(
        self,
        *,
        issuer: str,
        subject: str,
        tenant_external_id: str,
    ) -> ResolvedIdentityReferences:
        """Return stable references or one configured invalid outcome."""

        self.calls.append((issuer, subject, tenant_external_id))
        if self.error is not None:
            raise self.error
        if self.return_invalid_result:
            return object()  # type: ignore[return-value]
        return self.references


@pytest.fixture(scope="session")
def key_material() -> KeyMaterial:
    """Generate one ephemeral RSA key for the complete test session."""

    private_key = rsa.generate_private_key(public_exponent=65_537, key_size=2_048)
    public_jwk = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
    public_jwk.update({"kid": "key-1", "alg": "RS256", "use": "sig"})
    return KeyMaterial(private_key=private_key, public_jwk=public_jwk)


@pytest.fixture
def oidc_config() -> KeyverseOidcConfig:
    """Return the strict default test issuer profile."""

    return KeyverseOidcConfig(
        issuer="https://identity.example.test/realms/orgmetra",
        audience="orgmetra-people-api",
    )


@pytest.fixture
def jwks_provider(key_material: KeyMaterial) -> FakeJwksProvider:
    """Return a provider containing the session test signing key."""

    return FakeJwksProvider({"keys": [dict(key_material.public_jwk)]})


@pytest.fixture
def identity_resolver() -> FakeIdentityResolver:
    """Return a deterministic identity-reference resolver."""

    return FakeIdentityResolver()


def encode_token(
    key_material: KeyMaterial,
    config: KeyverseOidcConfig,
    *,
    payload_overrides: Mapping[str, object] | None = None,
    header_overrides: Mapping[str, object] | None = None,
    algorithm: str = "RS256",
    signing_key: object | None = None,
) -> str:
    """Create one short-lived JWT access token with optional hostile overrides."""

    now = int(time.time())
    payload: dict[str, object] = {
        "iss": config.issuer,
        "sub": "keyverse-subject-1",
        "aud": config.audience,
        "iat": now - 5,
        "exp": now + 300,
        "jti": "token-1",
        config.tenant_claim_name: "customer-1",
        config.purposes_claim_name: ["people_read", "people_admin"],
    }
    if payload_overrides:
        payload.update(payload_overrides)
    headers: dict[str, object] = {
        "kid": "key-1",
        "typ": "at+jwt",
    }
    if header_overrides:
        headers.update(header_overrides)
    return jwt.encode(
        payload,
        signing_key or key_material.private_key,
        algorithm=algorithm,
        headers=headers,
    )
