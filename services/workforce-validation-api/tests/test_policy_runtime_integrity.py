"""Regression for executable policy scalar values at the validation boundary."""

from __future__ import annotations

from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api.registry import (
    ValidationPrincipal,
    ValidityStudyReadPort,
    read_validity_study,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000c1")


class _ExecutableText(str):
    """Trip if authorization compares this caller-defined string subtype."""

    calls = 0
    __hash__ = str.__hash__

    def __eq__(self, other: object) -> bool:
        """Expose any equality comparison before the boundary rejects the subtype."""
        type(self).calls += 1
        raise AssertionError("caller-defined policy comparison executed")

    def __ne__(self, other: object) -> bool:
        """Expose any inequality comparison before the boundary rejects the subtype."""
        type(self).calls += 1
        raise AssertionError("caller-defined policy comparison executed")


class _ReadPort:
    """Record whether persistence was reached."""

    def __init__(self) -> None:
        self.calls = 0

    def read_validity_study(self, *, tenant_record_id: UUID, validity_study_id: UUID) -> None:
        """Fail the test if a rejected policy reaches persistence."""
        del tenant_record_id, validity_study_id
        self.calls += 1
        return None


def test_policy_text_subtype_is_rejected_before_comparison_or_persistence() -> None:
    _ExecutableText.calls = 0
    port = _ReadPort()
    assert isinstance(port, ValidityStudyReadPort)
    policy = PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="validation-read-v1",
        resource_kind=_ExecutableText("validity_study_record"),
        purpose_code="validation_review",
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=frozenset({"study_status_code"}),
    )

    with pytest.raises(ValueError, match="policy resource_kind"):
        read_validity_study(
            principal=ValidationPrincipal(
                tenant_record_id=TENANT,
                actor_reference="person:analyst-1",
                granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
            ),
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            purpose_code="validation_review",
            requested_fields=frozenset({"study_status_code"}),
            policy=policy,
            read_port=port,
        )

    assert _ExecutableText.calls == 0
    assert port.calls == 0


def test_policy_field_subtype_is_rejected_before_comparison_or_persistence() -> None:
    _ExecutableText.calls = 0
    port = _ReadPort()
    assert isinstance(port, ValidityStudyReadPort)
    policy = PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="validation-read-v1",
        resource_kind="validity_study_record",
        purpose_code="validation_review",
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=frozenset({_ExecutableText("study_status_code")}),
    )

    with pytest.raises(ValueError, match="policy permitted_fields"):
        read_validity_study(
            principal=ValidationPrincipal(
                tenant_record_id=TENANT,
                actor_reference="person:analyst-1",
                granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
            ),
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            purpose_code="validation_review",
            requested_fields=frozenset({"study_status_code"}),
            policy=policy,
            read_port=port,
        )

    assert _ExecutableText.calls == 0
    assert port.calls == 0
