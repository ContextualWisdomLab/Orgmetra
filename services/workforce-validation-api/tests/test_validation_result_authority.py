"""Fail closed when a released result is not bound to exact weight/variance evidence."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.result_authority import (
    ValidationResultAuthorityIntegrityError,
    ValidationResultAuthorityNotFound,
    ValidationResultAuthorityReadPort,
    ValidationResultAuthorityRecord,
    ValidationResultAuthorityView,
    resolve_validation_result_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
OTHER_TENANT = UUID("10000000-0000-7000-8000-000000000002")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
RESULT_REFERENCE = "validation_analysis_result:11111111-1111-4111-8111-111111111111"
COMPATIBILITY_REFERENCE = (
    "weight_variance_compatibility_receipt:22222222-2222-4222-8222-222222222222"
)
OWNER_REFERENCE = "released_owner_contract:33333333-3333-4333-8333-333333333333"
RESULT_DIGEST = "1" * 64
COMPATIBILITY_DIGEST = "2" * 64
ANALYSIS_WEIGHT_DIGEST = "3" * 64
VARIANCE_DIGEST = "4" * 64
OWNER_DIGEST = "5" * 64
OWNER_RELEASED_AT = datetime(2026, 9, 17, 4, 0, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 17, 5, 0, tzinfo=timezone.utc)
USED_AT = datetime(2026, 9, 17, 6, 0, tzinfo=timezone.utc)
READ_FIELDS = frozenset(
    {
        "result_reference",
        "result_digest",
        "compatibility_receipt_reference",
        "compatibility_receipt_digest",
        "analysis_weight_receipt_digest",
        "variance_design_receipt_digest",
        "verification_status",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "released_at",
        "superseded_at",
    }
)


class _ReadPort:
    """Return one configured released result record and retain exact lookup coordinates."""

    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[tuple[object, ...]] = []

    def read_validation_result_authority(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        result_reference: str,
        result_digest: str,
        compatibility_receipt_reference: str,
        compatibility_receipt_digest: str,
        analysis_weight_receipt_digest: str,
        variance_design_receipt_digest: str,
        verification_status: str,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
    ) -> object:
        self.calls.append(
            (
                tenant_record_id,
                validity_study_id,
                result_reference,
                result_digest,
                compatibility_receipt_reference,
                compatibility_receipt_digest,
                analysis_weight_receipt_digest,
                variance_design_receipt_digest,
                verification_status,
                owner_contract_reference,
                owner_contract_version,
                owner_contract_digest,
            )
        )
        return self.result


class _ProtocolOnly(ValidationResultAuthorityReadPort):
    """Inherit only the Protocol placeholder, not a concrete owner capability."""


def _principal() -> ValidationPrincipal:
    return ValidationPrincipal(
        tenant_record_id=TENANT,
        actor_reference="person:validation-analyst-1",
        granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
    )


def _policy(*, purpose_code: str = "selection_validity_analysis") -> PurposeBoundAccessPolicy:
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="validation-result-authority-read-v2",
        resource_kind="validation_result_authority",
        purpose_code=purpose_code,
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=READ_FIELDS,
    )


def _record(**overrides: object) -> ValidationResultAuthorityRecord:
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "result_reference": RESULT_REFERENCE,
        "result_digest": RESULT_DIGEST,
        "compatibility_receipt_reference": COMPATIBILITY_REFERENCE,
        "compatibility_receipt_digest": COMPATIBILITY_DIGEST,
        "analysis_weight_receipt_digest": ANALYSIS_WEIGHT_DIGEST,
        "variance_design_receipt_digest": VARIANCE_DIGEST,
        "verification_status": "verification_pending",
        "owner_contract_reference": OWNER_REFERENCE,
        "owner_contract_version": 7,
        "owner_contract_digest": OWNER_DIGEST,
        "owner_contract_released_at": OWNER_RELEASED_AT,
        "released_at": RELEASED_AT,
    }
    values.update(overrides)
    return ValidationResultAuthorityRecord(**values)


def _resolve(*, read_port: object, **overrides: object) -> ValidationResultAuthorityView:
    values: dict[str, object] = {
        "principal": _principal(),
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "result_reference": RESULT_REFERENCE,
        "result_digest": RESULT_DIGEST,
        "compatibility_receipt_reference": COMPATIBILITY_REFERENCE,
        "compatibility_receipt_digest": COMPATIBILITY_DIGEST,
        "analysis_weight_receipt_digest": ANALYSIS_WEIGHT_DIGEST,
        "variance_design_receipt_digest": VARIANCE_DIGEST,
        "verification_status": "verification_pending",
        "owner_contract_reference": OWNER_REFERENCE,
        "owner_contract_version": 7,
        "owner_contract_digest": OWNER_DIGEST,
        "used_at": USED_AT,
        "purpose_code": "selection_validity_analysis",
        "policy": _policy(),
        "read_port": read_port,
    }
    values.update(overrides)
    return resolve_validation_result_authority(**values)


def test_resolution_binds_result_to_exact_compatibility_and_owner_evidence() -> None:
    port = _ReadPort(_record())

    view = _resolve(read_port=port)

    assert isinstance(port, ValidationResultAuthorityReadPort)
    assert port.calls == [
        (
            TENANT,
            STUDY,
            RESULT_REFERENCE,
            RESULT_DIGEST,
            COMPATIBILITY_REFERENCE,
            COMPATIBILITY_DIGEST,
            ANALYSIS_WEIGHT_DIGEST,
            VARIANCE_DIGEST,
            "verification_pending",
            OWNER_REFERENCE,
            7,
            OWNER_DIGEST,
        )
    ]
    assert view.tenant_record_id == TENANT
    assert view.validity_study_id == STUDY
    fields = dict(view.fields)
    assert fields["result_digest"] == RESULT_DIGEST
    assert fields["compatibility_receipt_digest"] == COMPATIBILITY_DIGEST
    assert fields["analysis_weight_receipt_digest"] == ANALYSIS_WEIGHT_DIGEST
    assert fields["variance_design_receipt_digest"] == VARIANCE_DIGEST
    assert fields["verification_status"] == "verification_pending"
    assert fields["owner_contract_digest"] == OWNER_DIGEST
    assert fields["owner_contract_released_at"] == OWNER_RELEASED_AT
    assert fields["released_at"] == RELEASED_AT
    assert fields["superseded_at"] is None


def test_not_verifiable_result_remains_released_non_authorizing_evidence() -> None:
    record = _record(verification_status="not_verifiable")
    view = _resolve(
        read_port=_ReadPort(record),
        verification_status="not_verifiable",
    )
    assert dict(view.fields)["verification_status"] == "not_verifiable"


def test_authorization_denial_happens_before_owner_resolution() -> None:
    port = _ReadPort(_record())
    with pytest.raises(AuthorizationDeniedError):
        _resolve(read_port=port, policy=_policy(purpose_code="audit_review"))
    assert port.calls == []


def test_missing_noncanonical_or_mismatched_owner_evidence_fails_closed() -> None:
    with pytest.raises(ValidationResultAuthorityNotFound):
        _resolve(read_port=_ReadPort(None))
    with pytest.raises(ValidationResultAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(object()))
    with pytest.raises(ValidationResultAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(_record(result_digest="a" * 64)))


def test_distinct_evidence_digests_and_non_authorizing_status_are_required() -> None:
    with pytest.raises(ValueError):
        _record(compatibility_receipt_digest=RESULT_DIGEST)
    with pytest.raises(ValueError):
        _resolve(
            read_port=_ReadPort(_record()),
            variance_design_receipt_digest=ANALYSIS_WEIGHT_DIGEST,
        )
    with pytest.raises(ValueError):
        _record(verification_status=1)
    with pytest.raises(ValueError):
        _record(verification_status="verified")


def test_invalid_dependencies_and_pre_release_use_fail_closed() -> None:
    with pytest.raises(TypeError):
        _resolve(read_port=object())
    with pytest.raises(TypeError):
        _resolve(read_port=_ProtocolOnly())
    with pytest.raises(TypeError):
        _resolve(read_port=_ReadPort(_record()), principal=object())
    with pytest.raises(TypeError):
        _resolve(read_port=_ReadPort(_record()), policy=object())

    port = _ReadPort(_record())
    with pytest.raises(ValidationResultAuthorityIntegrityError):
        _resolve(
            read_port=port,
            used_at=datetime(2026, 9, 17, 4, 59, tzinfo=timezone.utc),
        )
    assert len(port.calls) == 1


def test_record_and_view_are_immutable_and_public_view_construction_is_blocked() -> None:
    record = _record()
    with pytest.raises(AttributeError):
        object.__setattr__(record, "verification_status", "not_verifiable")

    view = _resolve(read_port=_ReadPort(record))
    with pytest.raises(AttributeError):
        object.__setattr__(view, "fields", ())
    with pytest.raises(TypeError):
        ValidationResultAuthorityView(
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            fields=(),
        )


def test_cross_tenant_owner_evidence_is_rejected() -> None:
    with pytest.raises(ValidationResultAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(_record(tenant_record_id=OTHER_TENANT)))
