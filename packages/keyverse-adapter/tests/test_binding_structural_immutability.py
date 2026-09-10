"""Regression contract for post-validation Keyverse candidate integrity."""

from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import validate_identity_subject_candidate

TENANT = UUID("10000000-0000-7000-8000-000000000431")
PERSON = UUID("10000000-0000-7000-8000-000000000432")
ISSUER = "https://keyverse.example/issuer"
SUBJECT = "sub_structural_integrity"


def test_validated_candidate_cannot_be_rewritten_after_validation() -> None:
    """Validated candidate fields remain unchanged after low-level attribute replacement attempts."""
    candidate = validate_identity_subject_candidate(
        tenant_record_id=TENANT,
        person_record_id=PERSON,
        identity_issuer=ISSUER,
        identity_subject=SUBJECT,
    )

    with pytest.raises((AttributeError, TypeError)):
        object.__setattr__(candidate, "identity_subject", "sub_rewritten_after_validation")

    assert candidate.identity_subject == SUBJECT
