"""Regression contract for UUID storage behind immutable registry value objects."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api.registry import (
    ValidationPrincipal,
    ValidityStudyRecord,
    read_validity_study,
)

TENANT_TEXT = "10000000-0000-7000-8000-000000000001"
OTHER_TENANT = UUID("10000000-0000-7000-8000-000000000002")
STUDY_TEXT = "00000000-0000-7000-8000-0000000000c1"
OTHER_STUDY = UUID("00000000-0000-7000-8000-0000000000c2")
CRITERION_TEXT = "00000000-0000-7000-8000-0000000000a1"
OTHER_CRITERION = UUID("00000000-0000-7000-8000-0000000000a2")
RECORDED_FROM = datetime(2026, 11, 3, tzinfo=timezone.utc)


class _ReadPort:
    """Return one configured owner record for UUID-storage regression coverage."""

    def __init__(self, result: ValidityStudyRecord) -> None:
        self.result = result

    def read_validity_study(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
    ) -> ValidityStudyRecord:
        """Return the configured record after the application boundary authorizes the read."""
        return self.result


def _policy() -> PurposeBoundAccessPolicy:
    """Return the canonical purpose-bound policy for the regression read."""
    return PurposeBoundAccessPolicy(
        tenant_record_id=UUID(TENANT_TEXT),
        policy_version_code="validation-read-v1",
        resource_kind="validity_study_record",
        purpose_code="validation_review",
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=frozenset({"criterion_blueprint_id"}),
    )


def test_principal_and_record_do_not_retain_mutable_uuid_inputs() -> None:
    """Retained UUID aliases cannot rewrite identity evidence after constructor validation."""
    tenant = UUID(TENANT_TEXT)
    study = UUID(STUDY_TEXT)
    criterion = UUID(CRITERION_TEXT)
    principal = ValidationPrincipal(
        tenant_record_id=tenant,
        actor_reference="person:analyst-1",
        granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
    )
    record = ValidityStudyRecord(
        tenant_record_id=tenant,
        validity_study_id=study,
        criterion_blueprint_id=criterion,
        study_status_code="study_draft",
        recorded_from=RECORDED_FROM,
        recorded_to=None,
    )

    object.__setattr__(tenant, "int", OTHER_TENANT.int)
    object.__setattr__(study, "int", OTHER_STUDY.int)
    object.__setattr__(criterion, "int", OTHER_CRITERION.int)

    assert principal.tenant_record_id == UUID(TENANT_TEXT)
    assert record.tenant_record_id == UUID(TENANT_TEXT)
    assert record.validity_study_id == UUID(STUDY_TEXT)
    assert record.criterion_blueprint_id == UUID(CRITERION_TEXT)


def test_authorized_view_does_not_retain_or_expose_mutable_uuid_storage() -> None:
    """Target and projected UUID evidence remain stable across retained-reference rewrites."""
    tenant = UUID(TENANT_TEXT)
    study = UUID(STUDY_TEXT)
    principal = ValidationPrincipal(
        tenant_record_id=UUID(TENANT_TEXT),
        actor_reference="person:analyst-1",
        granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
    )
    record = ValidityStudyRecord(
        tenant_record_id=UUID(TENANT_TEXT),
        validity_study_id=UUID(STUDY_TEXT),
        criterion_blueprint_id=UUID(CRITERION_TEXT),
        study_status_code="study_draft",
        recorded_from=RECORDED_FROM,
        recorded_to=None,
    )

    view = read_validity_study(
        principal=principal,
        tenant_record_id=tenant,
        validity_study_id=study,
        purpose_code="validation_review",
        requested_fields=frozenset({"criterion_blueprint_id"}),
        policy=_policy(),
        read_port=_ReadPort(record),
    )

    object.__setattr__(tenant, "int", OTHER_TENANT.int)
    object.__setattr__(study, "int", OTHER_STUDY.int)
    projected_criterion = dict(view.fields)["criterion_blueprint_id"]
    assert type(projected_criterion) is UUID
    object.__setattr__(projected_criterion, "int", OTHER_CRITERION.int)

    assert view.tenant_record_id == UUID(TENANT_TEXT)
    assert view.validity_study_id == UUID(STUDY_TEXT)
    assert dict(view.fields)["criterion_blueprint_id"] == UUID(CRITERION_TEXT)
