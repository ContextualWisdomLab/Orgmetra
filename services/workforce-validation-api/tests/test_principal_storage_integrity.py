"""Regression contract for canonical validation-principal storage before authorization."""

from __future__ import annotations

from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api.registry import (
    ValidationPrincipal,
    ValidityStudyRecord,
    read_validity_study,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000c1")


class _ExecutableUUID(UUID):
    """Expose executable behavior if a UUID subtype reaches downstream validation."""

    def __getattribute__(self, name: str) -> object:
        if name == "int":
            raise AttributeError("UUID subtype behavior executed")
        return super().__getattribute__(name)


class _ReadPort:
    """Capture repository use; this regression must fail before persistence."""

    def __init__(self) -> None:
        self.calls: list[tuple[UUID, UUID]] = []

    def read_validity_study(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
    ) -> ValidityStudyRecord | None:
        """Record an unexpected persistence call."""
        self.calls.append((tenant_record_id, validity_study_id))
        return None


def _policy() -> PurposeBoundAccessPolicy:
    """Return the canonical purpose-bound policy used by the read boundary."""
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="validation-read-v1",
        resource_kind="validity_study_record",
        purpose_code="validation_review",
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=frozenset({"study_status_code"}),
    )


def test_low_level_exact_principal_is_revalidated_before_keyverse_evaluation() -> None:
    """Reject constructor-bypassed identity evidence before subtype behavior can execute."""
    forged_tenant = _ExecutableUUID(str(TENANT))
    principal = tuple.__new__(
        ValidationPrincipal,
        (
            forged_tenant,
            "person:analyst-1",
            frozenset({"orgmetra.workforce_validation.read"}),
        ),
    )
    port = _ReadPort()

    with pytest.raises(ValueError, match="tenant_record_id must be an exact operational UUID"):
        read_validity_study(
            principal=principal,
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            purpose_code="validation_review",
            requested_fields=frozenset({"study_status_code"}),
            policy=_policy(),
            read_port=port,
        )

    assert port.calls == []
