"""Opaque Keyverse subject binding without credential storage."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

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


@dataclass(frozen=True, slots=True)
class ExternalIdentityBinding:
    """Durable link from a Keyverse subject to an Orgmetra person."""

    tenant_record_id: UUID
    person_record_id: UUID
    identity_issuer: str
    identity_subject: str


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
        identity_issuer=identity_issuer.strip(),
        identity_subject=identity_subject.strip(),
    )
