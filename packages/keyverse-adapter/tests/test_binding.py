"""Keyverse adapter tests: validate candidates and reject untrusted binding authority."""

from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import (
    CredentialRejectedError,
    ExternalIdentityBindingCandidate,
    IdentityBindingTrustUnavailableError,
    bind_identity_subject,
    validate_identity_subject_candidate,
)

TENANT = UUID("10000000-0000-7000-8000-000000000401")
PERSON = UUID("10000000-0000-7000-8000-000000000402")
ISSUER = "https://keyverse.example/issuer"
SUBJECT = "sub_jordan_hale"


def _candidate(**overrides: object) -> ExternalIdentityBindingCandidate:
    """Build one valid non-authorizing candidate and override one field per test."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "person_record_id": PERSON,
        "identity_issuer": ISSUER,
        "identity_subject": SUBJECT,
    }
    values.update(overrides)
    return ExternalIdentityBindingCandidate(**values)  # type: ignore[arg-type]


def test_validate_identity_subject_candidate_keeps_only_opaque_subject() -> None:
    """Raw identity input may become validation data, never persistence authority."""
    candidate = validate_identity_subject_candidate(
        tenant_record_id=TENANT,
        person_record_id=PERSON,
        identity_issuer=ISSUER,
        identity_subject=SUBJECT,
        extra_claims={"purpose": "hr_operations"},
    )
    assert candidate.identity_subject == SUBJECT
    assert candidate.identity_issuer == ISSUER
    assert candidate.person_record_id == PERSON
    assert candidate.persistence_authorized is False


def test_bind_identity_subject_fails_closed_without_released_keyverse_trust() -> None:
    """Syntactically valid raw identity cannot manufacture a durable trusted binding."""
    with pytest.raises(IdentityBindingTrustUnavailableError) as caught:
        bind_identity_subject(
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            identity_issuer=ISSUER,
            identity_subject=SUBJECT,
            extra_claims={"purpose": "hr_operations"},
        )
    assert caught.value.next_action == "integrate_released_keyverse_subject_assertion_contract"


def test_candidate_validation_rejects_blank_issuer_or_subject() -> None:
    """Ask Keyverse for a real subject before creating even candidate identity data."""
    with pytest.raises(CredentialRejectedError, match="required"):
        validate_identity_subject_candidate(
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            identity_issuer="  ",
            identity_subject=SUBJECT,
        )
    with pytest.raises(CredentialRejectedError, match="required"):
        validate_identity_subject_candidate(
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            identity_issuer=ISSUER,
            identity_subject="",
        )


def test_bind_identity_subject_rejects_credential_claim_names_before_trust_gate() -> None:
    """Never copy a password, passkey, or token while evaluating identity input."""
    with pytest.raises(CredentialRejectedError, match="credentials"):
        bind_identity_subject(
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            identity_issuer=ISSUER,
            identity_subject=SUBJECT,
            extra_claims={"password": "not-a-secret-we-will-store"},
        )
    with pytest.raises(CredentialRejectedError, match="credentials"):
        bind_identity_subject(
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            identity_issuer=ISSUER,
            identity_subject=SUBJECT,
            extra_claims={"Access_Token": "header.payload.sig"},
        )


def test_candidate_rejects_non_uuid_tenant_or_person_identity() -> None:
    """Never retain candidate person linkage under a non-UUID identifier."""
    with pytest.raises(ValueError, match="tenant_record_id must be an operational UUID"):
        _candidate(tenant_record_id="not-a-uuid")
    with pytest.raises(ValueError, match="person_record_id must be an operational UUID"):
        _candidate(person_record_id=123)


def test_candidate_rejects_reserved_uuid_sentinels() -> None:
    """Never retain the protocol-reserved Nil or Max identity sentinels."""
    with pytest.raises(ValueError, match="tenant_record_id must be an operational UUID"):
        _candidate(tenant_record_id=UUID(int=0))
    with pytest.raises(ValueError, match="person_record_id must be an operational UUID"):
        _candidate(person_record_id=UUID(int=(1 << 128) - 1))


def test_candidate_rejects_forged_uuid_internal_integer_payload() -> None:
    """Reject an exact UUID whose internal integer was rewritten off-range."""
    forged = UUID("10000000-0000-7000-8000-000000000401")
    object.__setattr__(forged, "int", -1)
    with pytest.raises(ValueError, match="tenant_record_id must be an operational UUID"):
        _candidate(tenant_record_id=forged)

    out_of_range = UUID("10000000-0000-7000-8000-000000000402")
    object.__setattr__(out_of_range, "int", 1 << 128)
    with pytest.raises(ValueError, match="person_record_id must be an operational UUID"):
        _candidate(person_record_id=out_of_range)


def test_candidate_detaches_caller_owned_uuid_before_return() -> None:
    """Caller mutation after validation cannot rewrite retained candidate identity."""
    tenant = UUID("10000000-0000-7000-8000-000000000411")
    person = UUID("10000000-0000-7000-8000-000000000412")
    expected_tenant = UUID(int=tenant.int)
    expected_person = UUID(int=person.int)

    candidate = ExternalIdentityBindingCandidate(
        tenant_record_id=tenant,
        person_record_id=person,
        identity_issuer=ISSUER,
        identity_subject=SUBJECT,
    )

    assert candidate.tenant_record_id is not tenant
    assert candidate.person_record_id is not person
    object.__setattr__(tenant, "int", -1)
    object.__setattr__(person, "int", 1 << 128)
    assert candidate.tenant_record_id == expected_tenant
    assert candidate.person_record_id == expected_person


def test_candidate_rejects_text_subtypes_and_non_text_issuer_or_subject() -> None:
    """Require exact built-in text for issuer and subject candidate data."""

    class TextSubtype(str):
        pass

    with pytest.raises(ValueError, match="identity_issuer must be exact text"):
        _candidate(identity_issuer=TextSubtype(ISSUER))
    with pytest.raises(ValueError, match="identity_subject must be exact text"):
        _candidate(identity_subject=TextSubtype(SUBJECT))
    with pytest.raises(ValueError, match="identity_issuer must be exact text"):
        _candidate(identity_issuer=object())
    with pytest.raises(ValueError, match="identity_subject must be exact text"):
        _candidate(identity_subject=object())


def test_candidate_rejects_trimmed_empty_or_padded_issuer_or_subject() -> None:
    """Reject missing identity and preserve the bounded canonical text exactly."""
    with pytest.raises(ValueError, match="identity_issuer must be non-blank text"):
        _candidate(identity_issuer="   ")
    with pytest.raises(ValueError, match="identity_subject must be non-blank text"):
        _candidate(identity_subject="\t")
    with pytest.raises(ValueError, match="identity_issuer must be canonical text"):
        _candidate(identity_issuer=f" {ISSUER} ")
    with pytest.raises(ValueError, match="identity_subject must be canonical text"):
        _candidate(identity_subject=f"{SUBJECT}\n")


def test_bind_identity_subject_rejects_untrusted_runtime_types_before_trust_gate() -> None:
    """Reject forged identity inputs before reporting missing owner trust evidence."""

    class TextSubtype(str):
        pass

    class DuckText:
        def __init__(self, value: str) -> None:
            self._value = value

        def strip(self) -> str:
            return self._value

    with pytest.raises(ValueError, match="tenant_record_id must be an operational UUID"):
        bind_identity_subject(
            tenant_record_id=UUID(int=0),
            person_record_id=PERSON,
            identity_issuer=ISSUER,
            identity_subject=SUBJECT,
        )
    with pytest.raises(ValueError, match="identity_issuer must be exact text"):
        bind_identity_subject(
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            identity_issuer=DuckText(ISSUER),
            identity_subject=SUBJECT,
        )
    with pytest.raises(ValueError, match="identity_subject must be exact text"):
        bind_identity_subject(
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            identity_issuer=ISSUER,
            identity_subject=TextSubtype(SUBJECT),
        )
    with pytest.raises(ValueError, match="identity_subject must be canonical text"):
        bind_identity_subject(
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            identity_issuer=ISSUER,
            identity_subject=f" {SUBJECT} ",
        )


def test_extra_claims_reject_executable_container_or_key_before_use() -> None:
    """Do not execute caller-defined claim container or key behavior while rejecting credentials."""

    class ClaimsDict(dict[str, str]):
        def __len__(self) -> int:
            raise AssertionError("claim-container truthiness executed")

    class ClaimName(str):
        def lower(self) -> str:
            raise AssertionError("claim-name lower executed")

    with pytest.raises(ValueError, match="extra_claims must be an exact dict"):
        validate_identity_subject_candidate(
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            identity_issuer=ISSUER,
            identity_subject=SUBJECT,
            extra_claims=ClaimsDict({"purpose": "hr_operations"}),
        )

    with pytest.raises(ValueError, match="extra claim names must be exact text"):
        validate_identity_subject_candidate(
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            identity_issuer=ISSUER,
            identity_subject=SUBJECT,
            extra_claims={ClaimName("password"): "not-retained"},
        )


def test_extra_claims_reject_non_text_claim_name_with_bounded_error() -> None:
    """Malformed claim names fail closed without leaking an incidental AttributeError."""
    with pytest.raises(ValueError, match="extra claim names must be exact text"):
        validate_identity_subject_candidate(
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            identity_issuer=ISSUER,
            identity_subject=SUBJECT,
            extra_claims={object(): "not-retained"},  # type: ignore[dict-item]
        )
