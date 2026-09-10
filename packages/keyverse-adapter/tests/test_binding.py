"""Keyverse adapter tests: bind subjects, reject credentials."""

from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import (
    CredentialRejectedError,
    ExternalIdentityBinding,
    bind_identity_subject,
)

TENANT = UUID("10000000-0000-7000-8000-000000000401")
PERSON = UUID("10000000-0000-7000-8000-000000000402")
ISSUER = "https://keyverse.example/issuer"
SUBJECT = "sub_jordan_hale"


def _binding(**overrides: object) -> ExternalIdentityBinding:
    """Build one valid durable binding, letting each test override one field."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "person_record_id": PERSON,
        "identity_issuer": ISSUER,
        "identity_subject": SUBJECT,
    }
    values.update(overrides)
    return ExternalIdentityBinding(**values)  # type: ignore[arg-type]


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


def test_binding_rejects_non_uuid_tenant_or_person_identity() -> None:
    """Never persist a person link keyed by a non-UUID identifier."""
    with pytest.raises(ValueError, match="tenant_record_id must be an operational UUID"):
        _binding(tenant_record_id="not-a-uuid")
    with pytest.raises(ValueError, match="person_record_id must be an operational UUID"):
        _binding(person_record_id=123)


def test_binding_rejects_reserved_uuid_sentinels() -> None:
    """Never persist the protocol-reserved Nil or Max identity sentinels."""
    with pytest.raises(ValueError, match="tenant_record_id must be an operational UUID"):
        _binding(tenant_record_id=UUID(int=0))
    with pytest.raises(ValueError, match="person_record_id must be an operational UUID"):
        _binding(person_record_id=UUID(int=(1 << 128) - 1))


def test_binding_rejects_forged_uuid_internal_integer_payload() -> None:
    """Reject an exact UUID whose internal integer was rewritten off-range."""
    forged = UUID("10000000-0000-7000-8000-000000000401")
    object.__setattr__(forged, "int", -1)
    with pytest.raises(ValueError, match="tenant_record_id must be an operational UUID"):
        _binding(tenant_record_id=forged)

    out_of_range = UUID("10000000-0000-7000-8000-000000000402")
    object.__setattr__(out_of_range, "int", 1 << 128)
    with pytest.raises(ValueError, match="person_record_id must be an operational UUID"):
        _binding(person_record_id=out_of_range)


def test_binding_detaches_caller_owned_uuid_before_store_ready_return() -> None:
    """Caller mutation after construction cannot rewrite the validated binding identity."""
    tenant = UUID("10000000-0000-7000-8000-000000000411")
    person = UUID("10000000-0000-7000-8000-000000000412")
    expected_tenant = UUID(int=tenant.int)
    expected_person = UUID(int=person.int)

    binding = ExternalIdentityBinding(
        tenant_record_id=tenant,
        person_record_id=person,
        identity_issuer=ISSUER,
        identity_subject=SUBJECT,
    )

    assert binding.tenant_record_id is not tenant
    assert binding.person_record_id is not person
    object.__setattr__(tenant, "int", -1)
    object.__setattr__(person, "int", 1 << 128)
    assert binding.tenant_record_id == expected_tenant
    assert binding.person_record_id == expected_person


def test_binding_rejects_text_subtypes_and_non_text_issuer_or_subject() -> None:
    """Require exact built-in text for the durable issuer and subject."""

    class TextSubtype(str):
        pass

    with pytest.raises(ValueError, match="identity_issuer must be exact text"):
        _binding(identity_issuer=TextSubtype(ISSUER))
    with pytest.raises(ValueError, match="identity_subject must be exact text"):
        _binding(identity_subject=TextSubtype(SUBJECT))
    with pytest.raises(ValueError, match="identity_issuer must be exact text"):
        _binding(identity_issuer=object())
    with pytest.raises(ValueError, match="identity_subject must be exact text"):
        _binding(identity_subject=object())


def test_binding_rejects_trimmed_empty_or_padded_issuer_or_subject() -> None:
    """Reject missing identity and value the bounded canonical text exactly."""
    with pytest.raises(ValueError, match="identity_issuer must be non-blank text"):
        _binding(identity_issuer="   ")
    with pytest.raises(ValueError, match="identity_subject must be non-blank text"):
        _binding(identity_subject="\t")
    with pytest.raises(ValueError, match="identity_issuer must be canonical text"):
        _binding(identity_issuer=f" {ISSUER} ")
    with pytest.raises(ValueError, match="identity_subject must be canonical text"):
        _binding(identity_subject=f"{SUBJECT}\n")


def test_bind_identity_subject_rejects_untrusted_identity_runtime_types() -> None:
    """Reject forged identity inputs before returning a store-ready binding."""

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
