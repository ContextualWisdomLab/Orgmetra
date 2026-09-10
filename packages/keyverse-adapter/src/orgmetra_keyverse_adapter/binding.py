"""Validate Keyverse subject candidates without manufacturing authentication authority."""

from __future__ import annotations

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
        "id_token",
        "client_secret",
        "api_key",
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


def _validate_extra_claim_names(extra_claims: object) -> tuple[str, ...]:
    """Detach only inert canonical claim names needed for credential screening.

    Claim values are intentionally ignored because candidate validation does not
    retain or interpret them. Requiring an exact built-in ``dict`` and canonical
    exact built-in string keys avoids invoking caller-defined behavior and prevents
    surrounding whitespace from disguising a credential-shaped claim name.
    """
    if extra_claims is None:
        return ()
    if type(extra_claims) is not dict:
        raise ValueError("extra_claims must be an exact dict.")

    names: list[str] = []
    for name in extra_claims:
        if type(name) is not str:
            raise ValueError("extra claim names must be exact text.")
        names.append(_validate_canonical_text("extra claim name", name))
    return tuple(names)


class ExternalIdentityBindingCandidate(tuple):
    """Validated, structurally immutable identity candidate with no persistence authority.

    Tenant and person identities are exact operational UUIDs detached from
    caller-owned objects. Issuer and subject are canonical exact text. Tuple-backed
    storage prevents post-validation attribute replacement from changing the live
    candidate. This value still proves only local input integrity: low-level tuple
    construction can bypass the public constructor, so any consequential consumer
    must reconstruct or revalidate the evidence rather than treat this Python value
    as authentication or authorization authority.
    """

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        person_record_id: UUID,
        identity_issuer: str,
        identity_subject: str,
    ) -> ExternalIdentityBindingCandidate:
        """Validate and detach candidate evidence into immutable tuple storage."""
        tenant_identity = _validate_operational_uuid("tenant_record_id", tenant_record_id)
        person_identity = _validate_operational_uuid("person_record_id", person_record_id)
        issuer = _validate_canonical_text("identity_issuer", identity_issuer)
        subject = _validate_canonical_text("identity_subject", identity_subject)
        return tuple.__new__(
            cls,
            (
                UUID(int=tenant_identity),
                UUID(int=person_identity),
                issuer,
                subject,
            ),
        )

    @property
    def tenant_record_id(self) -> UUID:
        """Return the detached tenant identity."""
        return self[0]

    @property
    def person_record_id(self) -> UUID:
        """Return the detached Person identity."""
        return self[1]

    @property
    def identity_issuer(self) -> str:
        """Return the canonical issuer text retained at validation."""
        return self[2]

    @property
    def identity_subject(self) -> str:
        """Return the canonical opaque subject retained at validation."""
        return self[3]

    @property
    def persistence_authorized(self) -> bool:
        """Expose the invariant that locally validated candidate data never authorizes persistence."""
        return False


def _reject_missing_or_credential_input(
    *,
    identity_issuer: object,
    identity_subject: object,
    extra_claims: object,
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
    claim_names = _validate_extra_claim_names(extra_claims)
    forbidden = _FORBIDDEN_FIELD_NAMES.intersection(name.lower() for name in claim_names)
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
