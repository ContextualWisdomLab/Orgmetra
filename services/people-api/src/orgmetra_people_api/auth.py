"""Fail-closed request-edge authentication contracts for the People API.

Authentication proves who the caller is and which operation scopes were issued by
the identity boundary. HR purpose and field authorization are intentionally not
stored on this principal; Orgmetra evaluates those attributes through its
purpose-bound policy contract after the target resource has been resolved.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Protocol, runtime_checkable
from uuid import UUID

_MAX_UUID_INT = (1 << 128) - 1
_REFERENCE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$")
_SCOPE_PATTERN = re.compile(r"^orgmetra(?:\.[a-z][a-z0-9_]*){2,}$")


class AuthenticationFailed(RuntimeError):
    """Indicate that bearer authentication evidence is absent or malformed."""


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    """Identity attributes that may be trusted only after token authentication.

    ``tenant_record_id`` binds the authenticated actor to one Orgmetra tenant.
    ``actor_reference`` is opaque audit correlation rather than a person record
    identifier. ``granted_scope_codes`` carries explicit operation capabilities;
    it never carries an HR purpose decision.
    """

    tenant_record_id: UUID
    actor_reference: str
    granted_scope_codes: frozenset[str]

    def __post_init__(self) -> None:
        """Reject sentinel identities, runtime subtypes, wildcards, and bad references."""
        if type(self.tenant_record_id) is not UUID:
            raise ValueError("tenant_record_id must be a UUID.")
        if self.tenant_record_id.int in (0, _MAX_UUID_INT):
            raise ValueError("tenant_record_id must not use a reserved UUID sentinel.")
        if type(self.actor_reference) is not str or _REFERENCE_PATTERN.fullmatch(self.actor_reference) is None:
            raise ValueError("actor_reference must be a namespaced opaque reference.")
        if type(self.granted_scope_codes) is not frozenset or not self.granted_scope_codes:
            raise ValueError("granted_scope_codes must be a non-empty frozenset.")
        if any(type(scope) is not str or _SCOPE_PATTERN.fullmatch(scope) is None for scope in self.granted_scope_codes):
            raise ValueError("granted_scope_codes must contain explicit Orgmetra scopes.")

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Prevent executable principal subclasses from overriding authenticated evidence."""
        del kwargs
        raise TypeError("AuthenticatedPrincipal must not be subclassed")


@runtime_checkable
class TokenAuthenticator(Protocol):
    """Authenticate one bearer token without making an HR authorization decision."""

    async def authenticate(self, bearer_token: str) -> AuthenticatedPrincipal:
        """Return authenticated identity/scope attributes or raise a stable error."""


def extract_bearer_token(authorization_header: str | None) -> str:
    """Return one bounded printable bearer token without logging its value.

    Splitting only on the first ASCII space keeps C0 separators visible so they
    are rejected rather than silently treated as whitespace by ``str.split``.
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
