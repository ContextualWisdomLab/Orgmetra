"""Authentication and authorization contracts for the Orgmetra people API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from uuid import UUID


class AuthenticationFailed(RuntimeError):
    """Indicate that caller authentication evidence is absent or invalid."""


class AuthorizationDenied(RuntimeError):
    """Indicate that an authenticated principal lacks the required purpose."""


@dataclass(frozen=True, slots=True)
class AuthorizedPrincipal:
    """Represent an authenticated actor within one authorized tenant boundary."""

    tenant_reference: UUID
    actor_reference: UUID
    allowed_purpose_codes: frozenset[str]

    def __post_init__(self) -> None:
        """Require at least one bounded machine-readable purpose code."""

        if not self.allowed_purpose_codes:
            raise ValueError("allowed_purpose_codes must not be empty")
        normalized_codes = frozenset(
            _normalize_purpose_code(code) for code in self.allowed_purpose_codes
        )
        object.__setattr__(self, "allowed_purpose_codes", normalized_codes)


@runtime_checkable
class TokenAuthorizer(Protocol):
    """Validate a bearer token and authorize one server-selected purpose."""

    async def authorize(
        self, bearer_token: str, required_purpose_code: str
    ) -> AuthorizedPrincipal:
        """Return one principal or raise a stable authentication exception."""


def extract_bearer_token(authorization_header: str | None) -> str:
    """Return a bounded printable bearer token without logging its value."""

    if authorization_header is None:
        raise AuthenticationFailed("bearer authentication is required")
    parts = authorization_header.split()
    if len(parts) != 2 or parts[0].casefold() != "bearer":
        raise AuthenticationFailed("authorization must use the Bearer scheme")
    token = parts[1]
    if not token or len(token) > 8192:
        raise AuthenticationFailed("bearer token length is invalid")
    if any(ord(character) < 0x21 or ord(character) > 0x7E for character in token):
        raise AuthenticationFailed("bearer token contains invalid characters")
    return token


def ensure_purpose_authorized(
    principal: AuthorizedPrincipal, required_purpose_code: str
) -> None:
    """Fail closed when an authorizer returns an insufficient principal."""

    normalized_purpose = _normalize_purpose_code(required_purpose_code)
    if normalized_purpose not in principal.allowed_purpose_codes:
        raise AuthorizationDenied("required purpose is not authorized")


def _normalize_purpose_code(value: str) -> str:
    """Normalize one lower-case ASCII purpose code."""

    normalized = value.strip()
    if not normalized or len(normalized) > 128:
        raise ValueError("purpose code must contain at most 128 characters")
    if not all(
        character.isascii()
        and (character.islower() or character.isdigit() or character == "_")
        for character in normalized
    ):
        raise ValueError(
            "purpose code must use lower-case ASCII letters, digits, and underscores"
        )
    return normalized
