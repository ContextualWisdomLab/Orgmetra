"""Opaque Keyverse subject binding without credential storage."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

_MAX_UUID_INT = (1 << 128) - 1
_FORBIDDEN_FIELD_NAMES = frozenset(
    {
        "password",
        "passkey",
        "private_key",
        "secret",
        "credential",
        "refresh_token",
        "access_token",
    }
)


class CredentialRejectedError(ValueError):
    """A caller tried to persist a credential instead of an identity subject."""

    def __init__(self, message: str, *, next_action: str) -> None:
        """Tell the integrator to keep secrets in Keyverse."""
        super().__init__(message)
        self.next_action = next_action


def _validate_operational_uuid(field_name: str, value: object) -> None:
    """Require an exact UUID whose internal integer is a real operational identity.

    An exact ``uuid.UUID`` can still have its internal ``int`` slot rewritten with
    ``object.__setattr__``, so the retained payload must be proven to be an exact
    built-in integer inside the 128-bit construction range before the reserved
    Nil/Max sentinels are compared.
    """
    if type(value) is not UUID:
        raise ValueError(f"{field_name} must be an operational UUID.")
    identity = value.int
    if type(identity) is not int or not 0 <= identity <= _MAX_UUID_INT:
        raise ValueError(f"{field_name} must be an operational UUID.")
    if identity in (0, _MAX_UUID_INT):
        raise ValueError(f"{field_name} must be an operational UUID.")


def _validate_canonical_text(field_name: str, value: object) -> str:
    """Require exact built-in text that is non-blank and already canonical.

    The durable binding is a persisted link. Requiring the exact trimmed value
    prevents an executable ``str`` subtype or a ``strip``-shaped impostor from
    reaching the database while the audited value differs from the stored one.
    """
    if type(value) is not str:
        raise ValueError(f"{field_name} must be exact text.")
    if not value.strip():
        raise ValueError(f"{field_name} must be non-blank text.")
    if value != value.strip():
        raise ValueError(f"{field_name} must be canonical text without surrounding whitespace.")
    return value


@dataclass(frozen=True, slots=True)
class ExternalIdentityBinding:
    """Durable link from a Keyverse subject to an Orgmetra person.

    The persisted link is only useful if it addresses real, operational records.
    Both identities are validated as exact operational UUIDs and the issuer and
    subject as canonical exact text, so a store-ready binding can never key a
    person link on a sentinel, a non-UUID, or a credential-shaped value.
    """

    tenant_record_id: UUID
    person_record_id: UUID
    identity_issuer: str
    identity_subject: str

    def __post_init__(self) -> None:
        """Reject forged, sentinel, or non-canonical identity before persistence."""
        _validate_operational_uuid("tenant_record_id", self.tenant_record_id)
        _validate_operational_uuid("person_record_id", self.person_record_id)
        _validate_canonical_text("identity_issuer", self.identity_issuer)
        _validate_canonical_text("identity_subject", self.identity_subject)


def bind_identity_subject(
    *,
    tenant_record_id: UUID,
    person_record_id: UUID,
    identity_issuer: str,
    identity_subject: str,
    extra_claims: dict[str, str] | None = None,
) -> ExternalIdentityBinding:
    """Bind a Keyverse subject to a person after authentication succeeds.

    Args:
        tenant_record_id: Tenant that owns the person.
        person_record_id: Orgmetra person being linked.
        identity_issuer: Keyverse issuer URL or identifier.
        identity_subject: Opaque subject. Never a password or passkey.
        extra_claims: Optional non-secret claims. Secret field names are rejected.

    Returns:
        The binding to persist. Review it, then continue the HR action.
    """
    if type(identity_issuer) is not str:
        raise ValueError("identity_issuer must be exact text.")
    if type(identity_subject) is not str:
        raise ValueError("identity_subject must be exact text.")
    if not identity_issuer.strip() or not identity_subject.strip():
        raise CredentialRejectedError(
            "Identity issuer and subject are required.",
            next_action="Send the Keyverse issuer and opaque subject, then retry the bind.",
        )
    claims = extra_claims or {}
    forbidden = _FORBIDDEN_FIELD_NAMES.intersection(name.lower() for name in claims)
    if forbidden:
        raise CredentialRejectedError(
            "Identity binding cannot store credentials or tokens.",
            next_action="Keep secrets in Keyverse and send only the opaque subject.",
        )
    return ExternalIdentityBinding(
        tenant_record_id=tenant_record_id,
        person_record_id=person_record_id,
        identity_issuer=identity_issuer,
        identity_subject=identity_subject,
    )
