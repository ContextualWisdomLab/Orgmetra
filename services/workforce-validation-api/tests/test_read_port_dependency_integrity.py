"""Regression contracts for inert repository capability validation before authorization."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api.registry import (
    ValidationPrincipal,
    ValidityStudyReadPort,
    ValidityStudyRecord,
    read_validity_study,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000c1")
CRITERION = UUID("00000000-0000-7000-8000-0000000000a1")
RECORDED_FROM = datetime(2026, 11, 3, tzinfo=timezone.utc)


class _DescriptorReadPort:
    """Expose a non-callable static protocol member whose getter must never execute."""

    @property
    def read_validity_study(self) -> object:
        """Trip if dependency validation or later code executes this descriptor."""
        raise AssertionError("repository descriptor executed before rejection")


class _DynamicLookupReadPort:
    """Expose one safe class method but a different callable through instance lookup."""

    def __init__(self) -> None:
        self.dynamic_lookups = 0
        self.static_calls = 0

    def __getattribute__(self, name: str) -> object:
        """Trip if the authorized path performs a second dynamic capability lookup."""
        if name == "read_validity_study":
            dynamic_lookups = object.__getattribute__(self, "dynamic_lookups")
            object.__setattr__(self, "dynamic_lookups", dynamic_lookups + 1)

            def switched_capability(*, tenant_record_id: UUID, validity_study_id: UUID) -> object:
                del tenant_record_id, validity_study_id
                raise AssertionError("dynamic repository capability lookup executed after validation")

            return switched_capability
        return object.__getattribute__(self, name)

    def read_validity_study(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
    ) -> ValidityStudyRecord:
        """Return valid owner evidence when the statically validated method is invoked."""
        self.static_calls += 1
        return ValidityStudyRecord(
            tenant_record_id=tenant_record_id,
            validity_study_id=validity_study_id,
            criterion_blueprint_id=CRITERION,
            study_status_code="study_draft",
            recorded_from=RECORDED_FROM,
            recorded_to=None,
        )


class _InheritedProtocolReadPort(ValidityStudyReadPort):
    """Intentionally inherit the Protocol declaration without implementing persistence."""


def _principal() -> ValidationPrincipal:
    """Return one exact authenticated validation principal."""
    return ValidationPrincipal(
        tenant_record_id=TENANT,
        actor_reference="person:analyst-1",
        granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
    )


def _policy(*, purpose_code: str = "validation_review") -> PurposeBoundAccessPolicy:
    """Return one purpose-bound policy for the focused repository tests."""
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="validation-read-v1",
        resource_kind="validity_study_record",
        purpose_code=purpose_code,
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=frozenset({"study_status_code"}),
    )


def test_noncallable_repository_capability_fails_before_authorization() -> None:
    """Reject an invalid port before a deliberately denying policy can be evaluated."""
    with pytest.raises(TypeError, match="read_port must expose a statically callable read_validity_study"):
        read_validity_study(
            principal=_principal(),
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            purpose_code="validation_review",
            requested_fields=frozenset({"study_status_code"}),
            policy=_policy(purpose_code="audit_review"),
            read_port=_DescriptorReadPort(),  # type: ignore[arg-type]
        )


def test_inherited_protocol_placeholder_fails_before_authorization() -> None:
    """Require a concrete repository implementation before Keyverse policy evaluation."""
    with pytest.raises(TypeError, match="read_port must expose a statically callable read_validity_study"):
        read_validity_study(
            principal=_principal(),
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            purpose_code="validation_review",
            requested_fields=frozenset({"study_status_code"}),
            policy=_policy(purpose_code="audit_review"),
            read_port=_InheritedProtocolReadPort(),
        )


def test_validated_repository_capability_is_the_capability_invoked_after_authorization() -> None:
    """Bind the inertly validated class method instead of re-resolving it dynamically."""
    port = _DynamicLookupReadPort()

    view = read_validity_study(
        principal=_principal(),
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        purpose_code="validation_review",
        requested_fields=frozenset({"study_status_code"}),
        policy=_policy(),
        read_port=port,
    )

    assert port.dynamic_lookups == 0
    assert port.static_calls == 1
    assert view.fields == (("study_status_code", "study_draft"),)
