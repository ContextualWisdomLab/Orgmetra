"""Fail-closed request-edge authentication contracts for the People API.

Authentication proves who the caller is and which operation scopes were issued by
the identity boundary. HR purpose and field authorization are intentionally not
stored on this principal; Orgmetra evaluates those attributes through its
purpose-bound policy contract after the target resource has been resolved.
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


def _validate_retained_principal_payload(
    principal: "AuthenticatedPrincipal",
) -> tuple[int, str, frozenset[str]]:
    """Revalidate structurally retained authentication evidence before authority use."""
    if tuple.__len__(principal) != 3:
        raise ValueError("authenticated principal storage is malformed.")
    tenant_identity = tuple.__getitem__(principal, 0)
    actor_reference = tuple.__getitem__(principal, 1)
    granted_scope_codes = tuple.__getitem__(principal, 2)

    if type(tenant_identity) is not int or not 0 <= tenant_identity <= _MAX_UUID_INT:
        raise ValueError("tenant_record_id must contain an exact 128-bit integer identity.")
    if tenant_identity in (0, _MAX_UUID_INT):
        raise ValueError("tenant_record_id must not use a reserved UUID sentinel.")
    if type(actor_reference) is not str or _REFERENCE_PATTERN.fullmatch(actor_reference) is None:
        raise ValueError("actor_reference must be an exact namespaced opaque reference.")
    if type(granted_scope_codes) is not frozenset or not granted_scope_codes:
        raise ValueError("granted_scope_codes must be an exact non-empty frozenset.")
    if any(
        type(scope) is not str or _SCOPE_PATTERN.fullmatch(scope) is None
        for scope in granted_scope_codes
    ):
        raise ValueError("granted_scope_codes must contain exact explicit Orgmetra scopes.")
    return tenant_identity, actor_reference, granted_scope_codes


class AuthenticatedPrincipal(tuple):
    """Structurally immutable authenticated identity/scope evidence.

    Tenant authority is retained only as an exact built-in integer scalar. Public
    UUID access reconstructs a fresh view, so callers cannot mutate the principal's
    later tenant authority through a returned ``uuid.UUID`` alias. Actor and scope
    values remain exact built-in immutable scalars and never carry HR purpose.
    """

    __slots__ = ()

    def __new__(
        cls,
        tenant_record_id: UUID,
        actor_reference: str,
        granted_scope_codes: frozenset[str],
    ) -> "AuthenticatedPrincipal":
        """Validate and detach authentication evidence before retaining authority."""
        if type(tenant_record_id) is not UUID:
            raise ValueError("tenant_record_id must be an exact UUID.")
        tenant_identity = tenant_record_id.int
        if type(tenant_identity) is not int or not 0 <= tenant_identity <= _MAX_UUID_INT:
            raise ValueError("tenant_record_id must contain an exact 128-bit integer identity.")
        if tenant_identity in (0, _MAX_UUID_INT):
            raise ValueError("tenant_record_id must not use a reserved UUID sentinel.")
        if type(actor_reference) is not str or _REFERENCE_PATTERN.fullmatch(actor_reference) is None:
            raise ValueError("actor_reference must be an exact namespaced opaque reference.")
        if type(granted_scope_codes) is not frozenset or not granted_scope_codes:
            raise ValueError("granted_scope_codes must be an exact non-empty frozenset.")
        if any(
            type(scope) is not str or _SCOPE_PATTERN.fullmatch(scope) is None
            for scope in granted_scope_codes
        ):
            raise ValueError("granted_scope_codes must contain exact explicit Orgmetra scopes.")
        return tuple.__new__(
            cls,
            (tenant_identity, actor_reference, frozenset(granted_scope_codes)),
        )

    @property
    def tenant_record_id(self) -> UUID:
        """Return a fresh UUID view of the retained tenant scalar authority."""
        tenant_identity, _, _ = _validate_retained_principal_payload(self)
        return UUID(int=tenant_identity)

    @property
    def actor_reference(self) -> str:
        """Return the revalidated opaque authenticated actor reference."""
        _, actor_reference, _ = _validate_retained_principal_payload(self)
        return actor_reference

    @property
    def granted_scope_codes(self) -> frozenset[str]:
        """Return the revalidated exact operation-scope evidence."""
        _, _, granted_scope_codes = _validate_retained_principal_payload(self)
        return granted_scope_codes


@runtime_checkable
class TokenAuthenticator(Protocol):
    """Authenticate one bearer token without making an HR authorization decision."""

    async def authenticate(self, bearer_token: str) -> AuthenticatedPrincipal:
        """Return authenticated identity/scope attributes or raise a stable error."""


def extract_bearer_token(authorization_header: str | None) -> str:
    """Return one bounded printable bearer token without logging its value.

    Only exact built-in text is parsed. Splitting only on the first ASCII space
    keeps C0 separators visible so they are rejected rather than silently treated
    as whitespace by ``str.split``.
    """
    if authorization_header is None:
        raise AuthenticationFailed("bearer authentication is required")
    if type(authorization_header) is not str:
        raise AuthenticationFailed("authorization header must be exact text")
    parts = authorization_header.split(" ", 1)
    if len(parts) != 2 or parts[0].casefold() != "bearer":
        raise AuthenticationFailed("authorization must use the Bearer scheme")
    token = parts[1]
    if not token or len(token) > 8192:
        raise AuthenticationFailed("bearer token length is invalid")
    if any(ord(character) < 0x21 or ord(character) > 0x7E for character in token):
        raise AuthenticationFailed("bearer token contains invalid characters")
    return token
