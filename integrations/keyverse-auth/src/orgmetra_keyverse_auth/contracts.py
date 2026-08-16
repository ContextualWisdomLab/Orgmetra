"""Configuration and dependency ports for the Keyverse token authorizer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol, runtime_checkable
from urllib.parse import urlsplit
from uuid import UUID

_SUPPORTED_ALGORITHMS = frozenset({"RS256", "PS256", "ES256"})


@dataclass(frozen=True, slots=True)
class KeyverseOidcConfig:
    """Define the exact JWT access-token profile accepted by Orgmetra."""

    issuer: str
    audience: str
    tenant_claim_name: str = "orgmetra_tenant"
    purposes_claim_name: str = "orgmetra_purposes"
    allowed_algorithms: tuple[str, ...] = ("RS256",)
    required_token_type: str = "at+jwt"
    maximum_token_lifetime_seconds: int = 900
    clock_skew_seconds: int = 30

    def __post_init__(self) -> None:
        """Normalize bounded fields and reject permissive verification profiles."""

        issuer = self.issuer.strip()
        parsed_issuer = urlsplit(issuer)
        if (
            parsed_issuer.scheme != "https"
            or not parsed_issuer.hostname
            or parsed_issuer.username is not None
            or parsed_issuer.password is not None
            or parsed_issuer.query
            or parsed_issuer.fragment
        ):
            raise ValueError(
                "issuer must be an absolute credential-free HTTPS URL without query or fragment"
            )
        object.__setattr__(self, "issuer", issuer)

        audience = _bounded_printable(self.audience, "audience", 256)
        object.__setattr__(self, "audience", audience)
        object.__setattr__(
            self,
            "tenant_claim_name",
            _claim_name(self.tenant_claim_name, "tenant_claim_name"),
        )
        object.__setattr__(
            self,
            "purposes_claim_name",
            _claim_name(self.purposes_claim_name, "purposes_claim_name"),
        )

        algorithms = tuple(algorithm.strip() for algorithm in self.allowed_algorithms)
        if not algorithms or len(set(algorithms)) != len(algorithms):
            raise ValueError("allowed_algorithms must be a non-empty unique tuple")
        if not set(algorithms).issubset(_SUPPORTED_ALGORITHMS):
            raise ValueError("allowed_algorithms contains an unsupported algorithm")
        object.__setattr__(self, "allowed_algorithms", algorithms)

        token_type = _bounded_printable(
            self.required_token_type,
            "required_token_type",
            64,
        )
        object.__setattr__(self, "required_token_type", token_type)
        if not 60 <= self.maximum_token_lifetime_seconds <= 3_600:
            raise ValueError(
                "maximum_token_lifetime_seconds must be between 60 and 3600"
            )
        if not 0 <= self.clock_skew_seconds <= 120:
            raise ValueError("clock_skew_seconds must be between 0 and 120")


@dataclass(frozen=True, slots=True)
class ResolvedIdentityReferences:
    """Map external Keyverse identities to opaque Orgmetra references."""

    tenant_reference: UUID
    actor_reference: UUID


@runtime_checkable
class JwksProvider(Protocol):
    """Supply a bounded issuer-specific JWK set without verifier-owned egress."""

    async def get_jwks(self, issuer: str) -> Mapping[str, object]:
        """Return a JWK Set document for the exact configured issuer."""


@runtime_checkable
class IdentityReferenceResolver(Protocol):
    """Resolve external subject and tenant identifiers to Orgmetra UUIDs."""

    async def resolve(
        self,
        *,
        issuer: str,
        subject: str,
        tenant_external_id: str,
    ) -> ResolvedIdentityReferences:
        """Return opaque references or raise when mapping is unavailable."""


def _claim_name(value: str, field_name: str) -> str:
    """Normalize one lower-case ASCII JWT claim name."""

    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in value):
        raise ValueError(f"{field_name} must not contain control characters")
    normalized = value.strip()
    if not normalized or len(normalized) > 64:
        raise ValueError(f"{field_name} must contain at most 64 characters")
    if not all(
        character.isascii()
        and (character.islower() or character.isdigit() or character == "_")
        for character in normalized
    ):
        raise ValueError(
            f"{field_name} must use lower-case ASCII letters, digits, and underscores"
        )
    return normalized


def _bounded_printable(value: str, field_name: str, maximum_length: int) -> str:
    """Normalize one required printable value without control characters."""

    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in value):
        raise ValueError(f"{field_name} must not contain control characters")
    normalized = value.strip()
    if not normalized or len(normalized) > maximum_length:
        raise ValueError(
            f"{field_name} must contain at most {maximum_length} characters"
        )
    return normalized
