"""Regression contract for the workforce-validation study registry boundary."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api.registry import (
    ValidationPrincipal,
    ValidityStudyIntegrityError,
    ValidityStudyNotFound,
    ValidityStudyReadPort,
    ValidityStudyRecord,
    read_validity_study,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
OTHER_TENANT = UUID("10000000-0000-7000-8000-000000000002")
STUDY = UUID("00000000-0000-7000-8000-0000000000c1")
OTHER_STUDY = UUID("00000000-0000-7000-8000-0000000000c2")
CRITERION = UUID("00000000-0000-7000-8000-0000000000a1")
RECORDED_FROM = datetime(2026, 11, 3, tzinfo=timezone.utc)


class _ReadPort:
    """Return one configured registry record and capture the authorized target."""

    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[tuple[UUID, UUID]] = []

    def read_validity_study(self, *, tenant_record_id: UUID, validity_study_id: UUID) -> object:
        """Capture the target and return the configured persistence result."""
        self.calls.append((tenant_record_id, validity_study_id))
        return self.result


class _NoReadMethod:
    """Deliberately fail the runtime repository protocol."""


def _record(*, tenant_record_id: UUID = TENANT, validity_study_id: UUID = STUDY) -> ValidityStudyRecord:
    return ValidityStudyRecord(
        tenant_record_id=tenant_record_id,
        validity_study_id=validity_study_id,
        criterion_blueprint_id=CRITERION,
        study_status_code="study_draft",
        recorded_from=RECORDED_FROM,
        recorded_to=None,
    )


def _principal(*, tenant_record_id: UUID = TENANT) -> ValidationPrincipal:
    return ValidationPrincipal(
        tenant_record_id=tenant_record_id,
        actor_reference="person:analyst-1",
        granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
    )


def _policy(*, tenant_record_id: UUID = TENANT) -> PurposeBoundAccessPolicy:
    return PurposeBoundAccessPolicy(
        tenant_record_id=tenant_record_id,
        policy_version_code="validation-read-v1",
        resource_kind="validity_study_record",
        purpose_code="validation_review",
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=frozenset(
            {
                "criterion_blueprint_id",
                "study_status_code",
                "recorded_from",
                "recorded_to",
            }
        ),
    )


def test_read_returns_only_authorized_requested_fields() -> None:
    port = _ReadPort(_record())

    view = read_validity_study(
        principal=_principal(),
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        purpose_code="validation_review",
        requested_fields=frozenset({"study_status_code", "criterion_blueprint_id"}),
        policy=_policy(),
        read_port=port,
    )

    assert isinstance(port, ValidityStudyReadPort)
    assert port.calls == [(TENANT, STUDY)]
    assert view.tenant_record_id == TENANT
    assert view.validity_study_id == STUDY
    assert view.fields == (
        ("criterion_blueprint_id", CRITERION),
        ("study_status_code", "study_draft"),
    )


def test_authorization_denial_happens_before_persistence() -> None:
    port = _ReadPort(_record())

    with pytest.raises(AuthorizationDeniedError):
        read_validity_study(
            principal=_principal(),
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            purpose_code="validation_review",
            requested_fields=frozenset({"recorded_from"}),
            policy=PurposeBoundAccessPolicy(
                tenant_record_id=TENANT,
                policy_version_code="validation-read-v1",
                resource_kind="validity_study_record",
                purpose_code="audit_review",
                operation_code="read",
                required_scope_code="orgmetra.workforce_validation.read",
                permitted_fields=frozenset({"recorded_from"}),
            ),
            read_port=port,
        )

    assert port.calls == []


def test_missing_study_is_not_found() -> None:
    with pytest.raises(ValidityStudyNotFound):
        read_validity_study(
            principal=_principal(),
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            purpose_code="validation_review",
            requested_fields=frozenset({"study_status_code"}),
            policy=_policy(),
            read_port=_ReadPort(None),
        )


def test_foreign_or_noncanonical_persistence_result_fails_closed() -> None:
    for result in (_record(tenant_record_id=OTHER_TENANT), _record(validity_study_id=OTHER_STUDY), object()):
        with pytest.raises(ValidityStudyIntegrityError):
            read_validity_study(
                principal=_principal(),
                tenant_record_id=TENANT,
                validity_study_id=STUDY,
                purpose_code="validation_review",
                requested_fields=frozenset({"study_status_code"}),
                policy=_policy(),
                read_port=_ReadPort(result),
            )


def test_dependency_and_request_types_fail_before_repository_use() -> None:
    port = _ReadPort(_record())
    common = dict(
        principal=_principal(),
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        purpose_code="validation_review",
        requested_fields=frozenset({"study_status_code"}),
        policy=_policy(),
        read_port=port,
    )

    for key, value, error in (
        ("principal", object(), TypeError),
        ("policy", object(), TypeError),
        ("read_port", _NoReadMethod(), TypeError),
        ("tenant_record_id", "not-a-uuid", ValueError),
        ("validity_study_id", UUID(int=0), ValueError),
        ("purpose_code", "Validation Review", ValueError),
        ("purpose_code", 7, ValueError),
        ("requested_fields", set({"study_status_code"}), ValueError),
        ("requested_fields", frozenset(), ValueError),
        ("requested_fields", frozenset({"unknown_field"}), ValueError),
        ("requested_fields", frozenset({7}), ValueError),
    ):
        arguments = dict(common)
        arguments[key] = value
        with pytest.raises(error):
            read_validity_study(**arguments)

    assert port.calls == []


def test_principal_rejects_invalid_identity_and_scope_shapes() -> None:
    invalid_values = (
        dict(tenant_record_id=UUID(int=0), actor_reference="person:analyst-1", granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"})),
        dict(tenant_record_id=TENANT, actor_reference="not namespaced", granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"})),
        dict(tenant_record_id=TENANT, actor_reference=7, granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"})),
        dict(tenant_record_id=TENANT, actor_reference="person:analyst-1", granted_scope_codes=frozenset()),
        dict(tenant_record_id=TENANT, actor_reference="person:analyst-1", granted_scope_codes=frozenset({"bad-scope"})),
        dict(tenant_record_id=TENANT, actor_reference="person:analyst-1", granted_scope_codes=frozenset({7})),
    )
    for values in invalid_values:
        with pytest.raises(ValueError):
            ValidationPrincipal(**values)


def test_record_rejects_noncanonical_or_invalid_durable_scalars() -> None:
    valid = dict(
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        criterion_blueprint_id=CRITERION,
        study_status_code="study_draft",
        recorded_from=RECORDED_FROM,
        recorded_to=None,
    )
    cases = (
        ("tenant_record_id", UUID(int=0)),
        ("validity_study_id", "not-a-uuid"),
        ("criterion_blueprint_id", UUID(int=(1 << 128) - 1)),
        ("study_status_code", "Study Draft"),
        ("study_status_code", 7),
        ("recorded_from", datetime(2026, 11, 3)),
        ("recorded_to", "not-a-datetime"),
    )
    for field_name, value in cases:
        arguments = dict(valid)
        arguments[field_name] = value
        with pytest.raises(ValueError):
            ValidityStudyRecord(**arguments)

    with pytest.raises(ValueError):
        ValidityStudyRecord(**{**valid, "recorded_to": RECORDED_FROM})


def test_valid_record_detaches_supported_timezones_to_utc() -> None:
    for provider in (timezone(timedelta(hours=9)), ZoneInfo("Asia/Seoul")):
        record = ValidityStudyRecord(
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            criterion_blueprint_id=CRITERION,
            study_status_code="study_draft",
            recorded_from=datetime(2026, 11, 3, 9, tzinfo=provider),
            recorded_to=datetime(2026, 11, 4, 9, tzinfo=provider),
        )

        assert type(record.recorded_from) is datetime
        assert record.recorded_from.tzinfo is timezone.utc
        assert record.recorded_from.hour == 0
        assert record.recorded_to is not None
        assert record.recorded_to.tzinfo is timezone.utc


def test_record_is_structurally_immutable_against_object_setattr() -> None:
    record = _record()

    with pytest.raises(AttributeError):
        object.__setattr__(record, "study_status_code", "study_closed")

    assert record.study_status_code == "study_draft"
