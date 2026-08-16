"""Keyverse adapter tests: bind subjects, reject credentials."""

from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import (
    CredentialRejectedError,
    bind_identity_subject,
)

TENANT = UUID("10000000-0000-7000-8000-000000000401")
PERSON = UUID("10000000-0000-7000-8000-000000000402")


def test_bind_identity_subject_keeps_only_opaque_subject() -> None:
    """After login, store the Keyverse subject and continue the HR action."""
    binding = bind_identity_subject(
        tenant_record_id=TENANT,
        person_record_id=PERSON,
        identity_issuer="https://keyverse.example/issuer",
        identity_subject="sub_jordan_hale",
        extra_claims={"purpose": "hr_operations"},
    )
    assert binding.identity_subject == "sub_jordan_hale"
    assert binding.identity_issuer == "https://keyverse.example/issuer"
    assert binding.person_record_id == PERSON


def test_bind_identity_subject_rejects_blank_issuer_or_subject() -> None:
    """Ask Keyverse for a real subject before creating the person link."""
    with pytest.raises(CredentialRejectedError, match="required"):
        bind_identity_subject(
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            identity_issuer="  ",
            identity_subject="sub_jordan_hale",
        )
    with pytest.raises(CredentialRejectedError, match="required"):
        bind_identity_subject(
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            identity_issuer="https://keyverse.example/issuer",
            identity_subject="",
        )


def test_bind_identity_subject_rejects_credential_claim_names() -> None:
    """Never copy a password, passkey, or token onto the person record."""
    with pytest.raises(CredentialRejectedError, match="credentials"):
        bind_identity_subject(
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            identity_issuer="https://keyverse.example/issuer",
            identity_subject="sub_jordan_hale",
            extra_claims={"password": "not-a-secret-we-will-store"},
        )
    with pytest.raises(CredentialRejectedError, match="credentials"):
        bind_identity_subject(
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            identity_issuer="https://keyverse.example/issuer",
            identity_subject="sub_jordan_hale",
            extra_claims={"Access_Token": "header.payload.sig"},
        )
