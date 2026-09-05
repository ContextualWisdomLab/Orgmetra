"""Fail-closed request-edge authentication contracts for the People API.

Authentication proves who the caller is and which operation scopes were issued by
the identity boundary. HR purpose and field authorization are intentionally not
stored on this principal; Orgmetra evaluates those attributes through its
purpose-bound policy contract after the target resource has been resolved.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Iterator
from typing import Protocol, runtime_checkable
from uuid import UUID

_MAX_UUID_INT = (1 << 128) - 1
_REFERENCE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$")
_SCOPE_PATTERN = re.compile(r"^orgmetra(?:\.[a-z][a-z0-9_]*){2,}$")
_MAX_BEARER_TOKEN_LENGTH = 8192
_MAX_AUTHORIZATION_HEADER_LENGTH = 8199


def _validated_principal_storage(
    value: tuple[int, str, frozenset[str]],
) -> tuple[int, str, frozenset[str]]:
    """Return exact tuple-backed identity evidence or reject malformed storage.

    ``tuple.__new__`` can instantiate a tuple subclass without invoking that
    subclass's public constructor. Public principal behavior therefore cannot
    assume that tuple storage was validated merely because the runtime class is
    exact. Revalidating the raw built-in tuple slots keeps request-edge consumers
    fail-closed without treating Python construction history as policy authority.
    """
    if tuple.__len__(value) != 3:
        raise ValueError("stored authentication evidence is malformed.")
    tenant_record_id_int = tuple.__getitem__(value, 0)
    actor_reference = tuple.__getitem__(value, 1)
    granted_scope_codes = tuple.__getitem__(value, 2)
    if (
        type(tenant_record_id_int) is not int
        or not 0 <= tenant_record_id_int <= _MAX_UUID_INT
        or tenant_record_id_int in (0, _MAX_UUID_INT)
    ):
        raise ValueError("stored authentication evidence is malformed.")
    if type(actor_reference) is not str or _REFERENCE_PATTERN.fullmatch(actor_reference) is None:
        raise ValueError("stored authentication evidence is malformed.")
    if type(granted_scope_codes) is not frozenset or not granted_scope_codes:
        raise ValueError("stored authentication evidence is malformed.")
    if any(
        type(scope) is not str or _SCOPE_PATTERN.fullmatch(scope) is None
        for scope in granted_scope_codes
    ):
        raise ValueError("stored authentication evidence is malformed.")
    return tenant_record_id_int, actor_reference, granted_scope_codes


class AuthenticationFailed(RuntimeError):
    """Indicate that bearer authentication evidence is absent or malformed."""


class AuthenticatedPrincipal(tuple[int, str, frozenset[str]]):
    """Structurally immutable identity evidence returned by token authentication.

    ``tenant_record_id`` binds the authenticated actor to one Orgmetra tenant.
    ``actor_reference`` is opaque audit correlation rather than a person record
    identifier. ``granted_scope_codes`` carries explicit operation capabilities;
    it never carries an HR purpose decision.

    Tuple-backed storage deliberately leaves no writable instance slots. The
    tenant UUID is stored as its validated integer and reconstructed on access,
    so neither the caller's UUID nor a returned UUID aliases stored authority.
    Public access also revalidates all raw tuple slots because callers inside the
    service TCB can invoke ``tuple.__new__`` without this class's constructor.
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
        return tuple.__new__(cls, (tenant_record_id_int, actor_reference, granted_scope_codes))

    def __len__(self) -> int:
        """Report sequence length only after stored authentication evidence is valid."""
        _validated_principal_storage(self)
        return 3

    def __getitem__(
        self,
        key: int | slice,
    ) -> int | str | frozenset[str] | tuple[int, str, frozenset[str]]:
        """Expose sequence items only after all stored authentication evidence is valid."""
        return _validated_principal_storage(self)[key]

    def __iter__(self) -> Iterator[int | str | frozenset[str]]:
        """Iterate only after all stored authentication evidence is revalidated."""
        return iter(_validated_principal_storage(self))

    def __contains__(self, value: object) -> bool:
        """Search only revalidated authentication evidence."""
        return value in _validated_principal_storage(self)

    def count(self, value: object) -> int:
        """Count matches only in revalidated authentication evidence."""
        return _validated_principal_storage(self).count(value)

    def index(self, value: object, start: int = 0, stop: int = sys.maxsize) -> int:
        """Locate a value only in revalidated authentication evidence."""
        return _validated_principal_storage(self).index(value, start, stop)

    def __add__(self, other: tuple[object, ...]) -> tuple[object, ...]:
        """Concatenate only after this principal's stored evidence is revalidated."""
        return _validated_principal_storage(self) + other

    def __radd__(self, other: tuple[object, ...]) -> tuple[object, ...]:
        """Right-concatenate only after this principal's stored evidence is revalidated."""
        return other + _validated_principal_storage(self)

    def __mul__(self, count: int) -> tuple[object, ...]:
        """Repeat only revalidated authentication evidence."""
        return _validated_principal_storage(self) * count

    def __rmul__(self, count: int) -> tuple[object, ...]:
        """Right-repeat only revalidated authentication evidence."""
        return count * _validated_principal_storage(self)

    def __lt__(self, other: tuple[object, ...]) -> bool:
        """Order only after this principal's stored evidence is revalidated."""
        return _validated_principal_storage(self) < other

    def __le__(self, other: tuple[object, ...]) -> bool:
        """Order only after this principal's stored evidence is revalidated."""
        return _validated_principal_storage(self) <= other

    def __gt__(self, other: tuple[object, ...]) -> bool:
        """Order only after this principal's stored evidence is revalidated."""
        return _validated_principal_storage(self) > other

    def __ge__(self, other: tuple[object, ...]) -> bool:
        """Order only after this principal's stored evidence is revalidated."""
        return _validated_principal_storage(self) >= other

    @property
    def tenant_record_id(self) -> UUID:
        """Return a detached authenticated tenant identifier value."""
        tenant_record_id_int, _, _ = _validated_principal_storage(self)
        return UUID(int=tenant_record_id_int)

    @property
    def actor_reference(self) -> str:
        """Return the opaque authenticated actor correlation reference."""
        _, actor_reference, _ = _validated_principal_storage(self)
        return actor_reference

    @property
    def granted_scope_codes(self) -> frozenset[str]:
        """Return the exact operation scopes issued at authentication."""
        _, _, granted_scope_codes = _validated_principal_storage(self)
        return granted_scope_codes

    def __repr__(self) -> str:
        """Render the same field-oriented diagnostic shape as the prior value object."""
        tenant_record_id_int, actor_reference, granted_scope_codes = _validated_principal_storage(self)
        return (
            "AuthenticatedPrincipal("
            f"tenant_record_id={UUID(int=tenant_record_id_int)!r}, "
            f"actor_reference={actor_reference!r}, "
            f"granted_scope_codes={granted_scope_codes!r})"
        )

    def __eq__(self, other: object) -> bool:
        """Compare only another exact authenticated-principal value."""
        if type(other) is not AuthenticatedPrincipal:
            return False
        return _validated_principal_storage(self) == _validated_principal_storage(other)

    def __ne__(self, other: object) -> bool:
        """Keep inequality consistent with strict principal-only equality."""
        if type(other) is not AuthenticatedPrincipal:
            return True
        return _validated_principal_storage(self) != _validated_principal_storage(other)

    def __hash__(self) -> int:
        """Hash only revalidated immutable authentication evidence."""
        return hash(_validated_principal_storage(self))

    def __getnewargs__(self) -> tuple[UUID, str, frozenset[str]]:
        """Preserve validated constructor arguments for standard value reconstruction."""
        tenant_record_id_int, actor_reference, granted_scope_codes = _validated_principal_storage(self)
        return (UUID(int=tenant_record_id_int), actor_reference, granted_scope_codes)

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
    if type(authorization_header) is not str:
        raise AuthenticationFailed("authorization header must be plain text")
    if len(authorization_header) > _MAX_AUTHORIZATION_HEADER_LENGTH:
        raise AuthenticationFailed("authorization header length is invalid")
    parts = authorization_header.split(" ", 1)
    if len(parts) != 2 or parts[0].casefold() != "bearer":
        raise AuthenticationFailed("authorization must use the Bearer scheme")
    token = parts[1]
    if not token or len(token) > _MAX_BEARER_TOKEN_LENGTH:
        raise AuthenticationFailed("bearer token length is invalid")
    if any(ord(character) < 0x21 or ord(character) > 0x7E for character in token):
        raise AuthenticationFailed("bearer token contains invalid characters")
    return token
