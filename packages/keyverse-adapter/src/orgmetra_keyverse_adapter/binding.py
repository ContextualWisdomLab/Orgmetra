"""Validate Keyverse subject candidates without manufacturing authentication authority."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Never
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
    """A caller supplied missing identity data or credential material."""

    def __init__(self, message: str, *, next_action: str) -> None:
        """Retain one safe recovery action without retaining credential content."""
        super().__init__(message)
        self.next_action = next_action


class IdentityBindingTrustUnavailableError(RuntimeError):
    """A durable bind was requested without released Keyverse trust evidence."""

    def __init__(self) -> None:
        """Direct the caller to the owner-published trust contract instead of a local bypass."""
        super().__init__("Released Keyverse subject-assertion trust evidence is required for a durable binding.")
        self.next_action = "integrate_released_keyverse_subject_assertion_contract"


def _validate_operational_uuid(field_name: str, value: object) -> int:
    """Return the detached integer of one exact operational UUID.

    An exact ``uuid.UUID`` can still have its internal ``int`` slot rewritten with
    ``object.__setattr__``, so the retained payload must be proven to be an exact
    built-in integer inside the 128-bit construction range before the reserved
    Nil/Max sentinels are compared. Returning only the checked scalar lets the
    candidate reconstruct its own UUID instead of retaining a caller-owned alias.
    """
    if type(value) is not UUID:
        raise ValueError(f"{field_name} must be an operational UUID.")
    identity = value.int
    if type(identity) is not int or not 0 <= identity <= _MAX_UUID_INT:
        raise ValueError(f"{field_name} must be an operational UUID.")
    if identity in (0, _MAX_UUID_INT):
        raise ValueError(f"{field_name} must be an operational UUID.")
    return identity


def _validate_canonical_text(field_name: str, value: object) -> str:
    """Require exact built-in text that is non-blank and already canonical.

    Candidate identity still crosses a trust boundary even though it is not
    authorization evidence. Exact canonical text prevents executable ``str``
    subtypes or ``strip``-shaped impostors from surviving validation.
    """
    if type(value) is not str:
        raise ValueError(f"{field_name} must be exact text.")
    if not value.strip():
        raise ValueError(f"{field_name} must be non-blank text.")
    if value != value.strip():
        raise ValueError(f"{field_name} must be canonical text without surrounding whitespace.")
    return value


@dataclass(frozen=True, slots=True)
class ExternalIdentityBindingCandidate:
    """Validated identity candidate that carries no persistence authority.

    Tenant and person identities are exact operational UUIDs detached from
    caller-owned objects. Issuer and subject are canonical exact text. This value
    proves only local input integrity: it does not prove that Keyverse authenticated
    the subject, verified the issuer, or authorized a durable Orgmetra binding.
    """

    tenant_record_id: UUID
    person_record_id: UUID
    identity_issuer: str
    identity_subject: str

    def __post_init__(self) -> None:
        """Reject invalid identity and detach caller-owned UUIDs before returning candidate data."""
        tenant_identity = _validate_operational_uuid("tenant_record_id", self.tenant_record_id)
        person_identity = _validate_operational_uuid("person_record_id", self.person_record_id)
        _validate_canonical_text("identity_issuer", self.identity_issuer)
        _validate_canonical_text("identity_subject", self.identity_subject)
        object.__setattr__(self, "tenant_record_id", UUID(int=tenant_identity))
        object.__setattr__(self, "person_record_id", UUID(int=person_identity))

    @property
    def persistence_authorized(self) -> bool:
        """Expose the invariant that locally validated candidate data never authorizes persistence."""
        return False


def _reject_missing_or_credential_input(
    *,
    identity_issuer: object,
    identity_subject: object,
    extra_claims: dict[str, str] | None,
) -> None:
    """Reject absent identity and credential-shaped claim names before candidate construction."""
    if type(identity_issuer) is not str:
        raise ValueError("identity_issuer must be exact text.")
    if type(identity_subject) is not str:
        raise ValueError("identity_subject must be exact text.")
    if not identity_issuer.strip() or not identity_subject.strip():
        raise CredentialRejectedError(
            "Identity issuer and subject are required.",
            next_action="Send the Keyverse issuer and opaque subject, then retry validation.",
        )
    claims = extra_claims or {}
    forbidden = _FORBIDDEN_FIELD_NAMES.intersection(name.lower() for name in claims)
    if forbidden:
        raise CredentialRejectedError(
            "Identity validation cannot accept credentials or tokens.",
            next_action="Keep secrets in Keyverse and send only the opaque subject.",
        )


def validate_identity_subject_candidate(
    *,
    tenant_record_id: UUID,
    person_record_id: UUID,
    identity_issuer: str,
    identity_subject: str,
    extra_claims: dict[str, str] | None = None,
) -> ExternalIdentityBindingCandidate:
    """Validate raw identity input as non-authorizing candidate data.

    This function deliberately does not accept a trust flag or caller-created
    authentication receipt. A future positive binding path must consume the exact
    released/versioned Keyverse subject-assertion contract through an Orgmetra ACL.
    """
    _reject_missing_or_credential_input(
        identity_issuer=identity_issuer,
        identity_subject=identity_subject,
        extra_claims=extra_claims,
    )
    return ExternalIdentityBindingCandidate(
        tenant_record_id=tenant_record_id,
        person_record_id=person_record_id,
        identity_issuer=identity_issuer,
        identity_subject=identity_subject,
    )


def bind_identity_subject(
    *,
    tenant_record_id: UUID,
    person_record_id: UUID,
    identity_issuer: str,
    identity_subject: str,
    extra_claims: dict[str, str] | None = None,
) -> Never:
    """Fail closed until Keyverse publishes immutable subject-assertion trust evidence.

    Raw issuer/subject text is validated first so malformed or credential-bearing
    input still fails at the narrowest boundary. Successful syntax validation is
    not authentication evidence and therefore cannot produce a durable binding.
    """
    validate_identity_subject_candidate(
        tenant_record_id=tenant_record_id,
        person_record_id=person_record_id,
        identity_issuer=identity_issuer,
        identity_subject=identity_subject,
        extra_claims=extra_claims,
    )
    raise IdentityBindingTrustUnavailableError()
