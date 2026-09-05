"""Regression contract for inert repository capability validation before authorization."""

from __future__ import annotations

from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api.registry import (
    ValidationPrincipal,
    read_validity_study,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000c1")


class _DescriptorReadPort:
    """Expose a non-callable static protocol member whose getter must never execute."""

    @property
    def read_validity_study(self) -> object:
        """Trip if dependency validation or later code executes this descriptor."""
        raise AssertionError("repository descriptor executed before rejection")


def test_noncallable_repository_capability_fails_before_authorization() -> None:
    """Reject an invalid port before a deliberately denying policy can be evaluated."""
    principal = ValidationPrincipal(
        tenant_record_id=TENANT,
        actor_reference="person:analyst-1",
        granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
    )
    denying_policy = PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="validation-read-v1",
        resource_kind="validity_study_record",
        purpose_code="audit_review",
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=frozenset({"study_status_code"}),
    )

    with pytest.raises(TypeError, match="read_port must expose a statically callable read_validity_study"):
        read_validity_study(
            principal=principal,
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            purpose_code="validation_review",
            requested_fields=frozenset({"study_status_code"}),
            policy=denying_policy,
            read_port=_DescriptorReadPort(),  # type: ignore[arg-type]
        )
