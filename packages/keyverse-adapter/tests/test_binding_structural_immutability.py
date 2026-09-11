"""Regression contract for post-validation Keyverse candidate integrity."""

from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import validate_identity_subject_candidate

TENANT = UUID("10000000-0000-7000-8000-000000000431")
PERSON = UUID("10000000-0000-7000-8000-000000000432")
ISSUER = "https://keyverse.example/issuer"
SUBJECT = "sub_structural_integrity"


def _candidate():
    """Build one validated candidate for structural-integrity regressions."""
    return validate_identity_subject_candidate(
        tenant_record_id=TENANT,
        person_record_id=PERSON,
        identity_issuer=ISSUER,
        identity_subject=SUBJECT,
    )


def test_validated_candidate_cannot_be_rewritten_after_validation() -> None:
    """Validated candidate fields remain unchanged after low-level attribute replacement attempts."""
    candidate = _candidate()

    with pytest.raises((AttributeError, TypeError)):
        object.__setattr__(candidate, "identity_subject", "sub_rewritten_after_validation")

    assert candidate.identity_subject == SUBJECT


def test_returned_uuid_views_cannot_mutate_candidate_identity() -> None:
    """Caller mutation of returned UUID views cannot rewrite retained tenant or Person identity."""
    candidate = _candidate()
    tenant_view = candidate.tenant_record_id
    person_view = candidate.person_record_id

    object.__setattr__(tenant_view, "int", 0)
    object.__setattr__(person_view, "int", (1 << 128) - 1)

    assert candidate.tenant_record_id == TENANT
    assert candidate.person_record_id == PERSON
    assert candidate.tenant_record_id is not tenant_view
    assert candidate.person_record_id is not person_view
