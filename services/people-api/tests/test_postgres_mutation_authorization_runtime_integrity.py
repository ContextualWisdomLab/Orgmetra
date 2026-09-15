"""Adversarial runtime-integrity contract for PostgreSQL People mutation authorization."""

from __future__ import annotations

from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import AuthorizationDecision
from orgmetra_people_api.postgres_mutations import (
    PeopleMutationIntegrityError,
    _require_authorization,
)

TENANT = UUID("0198a412-7100-7000-8000-000000000001")
RESOURCE = "employment_record:0198a412710070008000000000000030"
FIELDS = frozenset({"employment_record"})


class ForgedAuthorizationDecision(AuthorizationDecision):
    """Represent a validation-bypassing caller-defined authorization subtype."""


def test_postgres_people_mutation_rejects_authorization_subclass() -> None:
    """Require persistence authorization to use the exact governed decision runtime type."""
    forged = ForgedAuthorizationDecision(
        allowed=True,
        tenant_record_id=TENANT,
        actor_reference="keyverse_subject:operator-17",
        resource_reference=RESOURCE,
        policy_version_code="people-employment-v1",
        purpose_code="workforce_admin",
        operation_code="create_record",
        resource_kind="employment_record",
        requested_fields=FIELDS,
        authorized_fields=FIELDS,
        reason_code="access_permitted",
        next_action="continue",
    )

    with pytest.raises(PeopleMutationIntegrityError, match="typed authorization decision"):
        _require_authorization(
            authorization=forged,
            tenant_record_id=TENANT,
            resource_reference=RESOURCE,
            resource_kind="employment_record",
            requested_fields=FIELDS,
        )
