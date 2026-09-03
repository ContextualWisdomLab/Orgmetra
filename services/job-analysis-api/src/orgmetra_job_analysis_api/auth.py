"""Fail-closed request-edge authentication for job-analysis persistence.

Authentication proves who the caller is and which operation scopes Keyverse
issued. Purpose-bound authorization stays outside this principal so a token
cannot smuggle an HR purpose grant.
"""

from __future__ import annotations

import re
from typing import Protocol, runtime_checkable
from uuid import UUID

_MAX_UUID_INT = (1 << 128) - 1
_REFERENCE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$")
_SCOPE_PATTERN = re.compile(r"^orgmetra(?:\.[a-z][a-z0-9_]*){2,}$")


class AuthenticationFailed(RuntimeError):
    """Indicate that bearer authentication evidence is absent or malformed."""


class AuthenticatedPrincipal(tuple[UUID, str, frozenset[str]]):
    """Structurally immutable identity evidence returned by token authentication.

    ``tenant_record_id`` binds the authenticated actor to one Orgmetra tenant.
    ``actor_reference`` is opaque audit correlation. ``granted_scope_codes``
    carries explicit operation capabilities and never an HR purpose decision.

    Tuple-backed storage deliberately leaves no writable instance slots. This
    prevents low-level field replacement after authentication while preserving
    value semantics for trusted service code.
    """

    __slots__ = ()
    __match_args__ = ("tenant_record_id", "actor_reference", "granted_scope_codes")

    def __new__(
        cls,
        tenant_record_id: UUID,
        actor_reference: str,
        granted_scope_codes: frozenset[str],
    ) -> AuthenticatedPrincipal:
        """Validate, detach, and store exact authentication evidence once."""
        if type(tenant_record_id) is not UUID:
            raise ValueError("tenant_record_id must be a UUID.")
        tenant_record_id_int = tenant_record_id.int
        if type(tenant_record_id_int) is not int or not 0 <= tenant_record_id_int <= _MAX_UUID_INT:
            raise ValueError("tenant_record_id must contain a valid UUID integer.")
        if tenant_record_id_int in (0, _MAX_UUID_INT):
            raise ValueError("tenant_record_id must not use a reserved UUID sentinel.")
        if type(actor_reference) is not str or _REFERENCE_PATTERN.fullmatch(actor_reference) is None:
            raise ValueError("actor_reference must be a namespaced opaque reference.")
        if type(granted_scope_codes) is not frozenset or not granted_scope_codes:
            raise ValueError("granted_scope_codes must be a non-empty frozenset.")
        if any(type(scope) is not str or _SCOPE_PATTERN.fullmatch(scope) is None for scope in granted_scope_codes):
            raise ValueError("granted_scope_codes must contain explicit Orgmetra scopes.")
        return tuple.__new__(cls, (UUID(int=tenant_record_id_int), actor_reference, granted_scope_codes))

    @property
    def tenant_record_id(self) -> UUID:
        """Return the detached authenticated tenant identifier."""
        return self[0]

    @property
    def actor_reference(self) -> str:
        """Return the opaque authenticated actor correlation reference."""
        return self[1]

    @property
    def granted_scope_codes(self) -> frozenset[str]:
        """Return the exact operation scopes issued at authentication."""
        return self[2]

    def __repr__(self) -> str:
        """Render the same field-oriented diagnostic shape as the prior value object."""
        return (
            "AuthenticatedPrincipal("
            f"tenant_record_id={self.tenant_record_id!r}, "
            f"actor_reference={self.actor_reference!r}, "
            f"granted_scope_codes={self.granted_scope_codes!r})"
        )

    def __eq__(self, other: object) -> bool:
        """Compare only another exact authenticated-principal value."""
        if type(other) is not AuthenticatedPrincipal:
            return False
        return tuple.__eq__(self, other)

    __hash__ = tuple.__hash__

    def __getnewargs__(self) -> tuple[UUID, str, frozenset[str]]:
        """Preserve validated constructor arguments for standard value reconstruction."""
        return (self.tenant_record_id, self.actor_reference, self.granted_scope_codes)

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
    """Return one bounded printable bearer token without logging its value."""
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
