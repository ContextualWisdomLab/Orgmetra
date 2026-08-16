"""Authentication and authorization contracts for the Orgmetra people API."""

from __future__ import annotations

from dataclasses import dataclass
from string import ascii_lowercase, digits
from typing import Protocol, runtime_checkable
from uuid import UUID

from orgmetra_postgres import RepositoryUnavailableError

_PURPOSE_CHARACTERS = frozenset(ascii_lowercase + digits + "_")
_SCOPE_CHARACTERS = frozenset(ascii_lowercase + digits + "_.:")


class AuthenticationFailed(RuntimeError):
    """Indicate that caller authentication evidence is absent or invalid."""


class AuthorizationDenied(RuntimeError):
    """Indicate that an authenticated principal lacks required authority."""


class IdentityProviderUnavailable(RepositoryUnavailableError):
    """Indicate a retryable identity-provider or identity-mapping outage."""


@dataclass(frozen=True, slots=True)
class AuthorizedPrincipal:
    """Represent an actor with independent capability scopes and HR purposes."""

    tenant_reference: UUID
    actor_reference: UUID
    allowed_scope_codes: frozenset[str]
    allowed_purpose_codes: frozenset[str]

    def __post_init__(self) -> None:
        """Require bounded machine-readable scope and purpose grants."""

        if not self.allowed_scope_codes:
            raise ValueError("allowed_scope_codes must not be empty")
        if not self.allowed_purpose_codes:
            raise ValueError("allowed_purpose_codes must not be empty")
        object.__setattr__(
            self,
            "allowed_scope_codes",
            frozenset(_normalize_scope_code(code) for code in self.allowed_scope_codes),
        )
        object.__setattr__(
            self,
            "allowed_purpose_codes",
            frozenset(
                _normalize_purpose_code(code) for code in self.allowed_purpose_codes
            ),
        )


@runtime_checkable
class TokenAuthorizer(Protocol):
    """Validate a token and authorize server-selected scope and purpose."""

    async def authorize(
        self,
        bearer_token: str,
        required_scope_code: str,
        required_purpose_code: str,
    ) -> AuthorizedPrincipal:
        """Return one principal or raise a stable authentication exception."""


def extract_bearer_token(authorization_header: str | None) -> str:
    """Return a bounded printable bearer token without logging its value.

    Split only on the first ASCII space. Default ``str.split()`` treats
    Unicode C0 separators such as ``\\x1f`` as whitespace, which would hide
    control characters inside the token instead of rejecting them.
    """

    if authorization_header is None:
        raise AuthenticationFailed("bearer authentication is required")
    parts = authorization_header.split(" ", 1)
    if len(parts) != 2 or parts[0].casefold() != "bearer":
        raise AuthenticationFailed("authorization must use the Bearer scheme")
    token = parts[1]
    if not token or len(token) > 8192:
        raise AuthenticationFailed("bearer token length is invalid")
    if any(ord(character) < 0x21 or ord(character) > 0x7E for character in token):
        raise AuthenticationFailed("bearer token contains invalid characters")
    return token


def ensure_scope_authorized(
    principal: AuthorizedPrincipal, required_scope_code: str
) -> None:
    """Fail closed when the token lacks the route's operation capability."""

    normalized_scope = _normalize_scope_code(required_scope_code)
    if normalized_scope not in principal.allowed_scope_codes:
        raise AuthorizationDenied("required scope is not authorized")


def ensure_purpose_authorized(
    principal: AuthorizedPrincipal, required_purpose_code: str
) -> None:
    """Fail closed when the actor lacks the route's lawful business purpose."""

    normalized_purpose = _normalize_purpose_code(required_purpose_code)
    if normalized_purpose not in principal.allowed_purpose_codes:
        raise AuthorizationDenied("required purpose is not authorized")


def _normalize_purpose_code(value: str) -> str:
    """Normalize one lower-case ASCII purpose code."""

    normalized = value.strip()
    if not normalized or len(normalized) > 64:
        raise ValueError("purpose code must contain at most 64 characters")
    if not all(character in _PURPOSE_CHARACTERS for character in normalized):
        raise ValueError(
            "purpose code must use lower-case ASCII letters, digits, and underscores"
        )
    return normalized


def _normalize_scope_code(value: str) -> str:
    """Normalize one bounded lower-case ASCII operation scope."""

    normalized = value.strip()
    if not normalized or len(normalized) > 128:
        raise ValueError("scope code must contain at most 128 characters")
    if not all(character in _SCOPE_CHARACTERS for character in normalized):
        raise ValueError(
            "scope code must use lower-case ASCII letters, digits, dots, colons, and underscores"
        )
    return normalized
