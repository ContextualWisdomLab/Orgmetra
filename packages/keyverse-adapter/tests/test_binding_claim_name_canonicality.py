"""Regression contracts for inert, canonical Keyverse claim names."""

from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import bind_identity_subject

TENANT = UUID("10000000-0000-7000-8000-000000000421")
PERSON = UUID("10000000-0000-7000-8000-000000000422")
ISSUER = "https://keyverse.example/issuer"
SUBJECT = "sub_claim_name_boundary"


def test_padded_credential_claim_name_fails_before_trust_gate() -> None:
    """Whitespace must not let a credential-shaped claim name evade screening."""
    with pytest.raises(ValueError, match="extra claim name must be canonical text"):
        bind_identity_subject(
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            identity_issuer=ISSUER,
            identity_subject=SUBJECT,
            extra_claims={" Access_Token ": "header.payload.sig"},
        )


def test_blank_claim_name_fails_before_trust_gate() -> None:
    """A blank claim name is malformed input rather than trusted candidate metadata."""
    with pytest.raises(ValueError, match="extra claim name must be non-blank text"):
        bind_identity_subject(
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            identity_issuer=ISSUER,
            identity_subject=SUBJECT,
            extra_claims={"   ": "ignored"},
        )
