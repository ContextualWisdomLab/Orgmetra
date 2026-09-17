"""RED contract for durable non-verifiability of validation-result evidence."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.result_nonverifiability import (
    ValidationResultNonVerifiabilityIntegrityError,
    ValidationResultNonVerifiabilityNotFound,
    ValidationResultNonVerifiabilityReadPort,
    ValidationResultNonVerifiabilityRecord,
    ValidationResultNonVerifiabilityView,
    resolve_validation_result_nonverifiability,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
OTHER_TENANT = UUID("10000000-0000-7000-8000-000000000002")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
RESULT_REFERENCE = "validation_analysis_result:11111111-1111-4111-8111-111111111111"
FAILED_WEIGHT_REFERENCE = "analysis_weight_receipt:22222222-2222-4222-8222-222222222222"
ATTEMPT_REFERENCE = (
    "validation_evidence_verification_attempt:33333333-3333-4333-8333-333333333333"
)
OWNER_REFERENCE = "released_owner_contract:44444444-4444-4444-8444-444444444444"
RESULT_DIGEST = "1" * 64
FAILED_WEIGHT_DIGEST = "2" * 64
ATTEMPT_DIGEST = "3" * 64
OWNER_DIGEST = "4" * 64
OWNER_CONTRACT_RELEASED_AT = datetime(2026, 9, 17, 5, 55, tzinfo=timezone.utc)
FAILED_EVIDENCE_RELEASED_AT = datetime(2026, 9, 17, 5, 59, tzinfo=timezone.utc)
EVALUATED_AT = datetime(2026, 9, 17, 6, 0, tzinfo=timezone.utc)
ATTEMPT_RELEASED_AT = datetime(2026, 9, 17, 6, 2, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 17, 6, 5, tzinfo=timezone.utc)
USED_AT = datetime(2026, 9, 17, 6, 10, tzinfo=timezone.utc)
READ_FIELDS = frozenset(
    {
        "result_reference",
        "result_digest",
        "verification_status",
        "failed_evidence_kind",
        "failure_mode",
        "failed_evidence_reference",
        "failed_evidence_digest",
        "failed_evidence_released_at",
        "verification_attempt_reference",
        "verification_attempt_digest",
        "verification_attempt_released_at",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "evaluated_at",
        "released_at",
        "superseded_at",
    }
)


class _ReadPort:
    """Return one configured owner outcome and retain exact lookup coordinates."""

    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[tuple[object, ...]] = []

    def read_validation_result_nonverifiability(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        result_reference: str,
        result_digest: str,
        failed_evidence_kind: str,
        failure_mode: str,
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
                failed_evidence_kind,
                failure_mode,
                owner_contract_reference,
                owner_contract_version,
                owner_contract_digest,
            )
        )
        return self.result


class _ProtocolOnly(ValidationResultNonVerifiabilityReadPort):
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
        policy_version_code="validation-result-nonverifiability-read-v1",
        resource_kind="validation_result_nonverifiability",
        purpose_code=purpose_code,
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=READ_FIELDS,
    )


def _record(**overrides: object) -> ValidationResultNonVerifiabilityRecord:
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "result_reference": RESULT_REFERENCE,
        "result_digest": RESULT_DIGEST,
        "failed_evidence_kind": "analysis_weight_receipt",
        "failure_mode": "missing",
        "failed_evidence_reference": None,
        "failed_evidence_digest": None,
        "failed_evidence_released_at": None,
        "verification_attempt_reference": ATTEMPT_REFERENCE,
        "verification_attempt_digest": ATTEMPT_DIGEST,
        "verification_attempt_released_at": ATTEMPT_RELEASED_AT,
        "owner_contract_reference": OWNER_REFERENCE,
        "owner_contract_version": 7,
        "owner_contract_digest": OWNER_DIGEST,
        "owner_contract_released_at": OWNER_CONTRACT_RELEASED_AT,
        "evaluated_at": EVALUATED_AT,
        "released_at": RELEASED_AT,
    }
    values.update(overrides)
    return ValidationResultNonVerifiabilityRecord(**values)


def _resolve(
    *, read_port: object, **overrides: object
) -> ValidationResultNonVerifiabilityView:
    values: dict[str, object] = {
        "principal": _principal(),
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "result_reference": RESULT_REFERENCE,
        "result_digest": RESULT_DIGEST,
        "failed_evidence_kind": "analysis_weight_receipt",
        "failure_mode": "missing",
        "owner_contract_reference": OWNER_REFERENCE,
        "owner_contract_version": 7,
        "owner_contract_digest": OWNER_DIGEST,
        "used_at": USED_AT,
        "purpose_code": "selection_validity_analysis",
        "policy": _policy(),
        "read_port": read_port,
    }
    values.update(overrides)
    return resolve_validation_result_nonverifiability(**values)


def test_missing_final_weight_evidence_is_released_as_not_verifiable() -> None:
    port = _ReadPort(_record())

    view = _resolve(read_port=port)

    assert isinstance(port, ValidationResultNonVerifiabilityReadPort)
    assert port.calls == [
        (
            TENANT,
            STUDY,
            RESULT_REFERENCE,
            RESULT_DIGEST,
            "analysis_weight_receipt",
            "missing",
            OWNER_REFERENCE,
            7,
            OWNER_DIGEST,
        )
    ]
    assert view.tenant_record_id == TENANT
    assert view.validity_study_id == STUDY
    fields = dict(view.fields)
    assert fields["verification_status"] == "not_verifiable"
    assert fields["failed_evidence_kind"] == "analysis_weight_receipt"
    assert fields["failure_mode"] == "missing"
    assert fields["failed_evidence_reference"] is None
    assert fields["failed_evidence_digest"] is None
    assert fields["failed_evidence_released_at"] is None
    assert fields["verification_attempt_reference"] == ATTEMPT_REFERENCE
    assert fields["verification_attempt_digest"] == ATTEMPT_DIGEST
    assert fields["verification_attempt_released_at"] == ATTEMPT_RELEASED_AT
    assert fields["owner_contract_released_at"] == OWNER_CONTRACT_RELEASED_AT
    assert fields["evaluated_at"] == EVALUATED_AT
    assert fields["released_at"] == RELEASED_AT
    assert fields["superseded_at"] is None


def test_non_reproducible_weight_evidence_keeps_exact_failed_receipt() -> None:
    record = _record(
        failure_mode="non_reproducible",
        failed_evidence_reference=FAILED_WEIGHT_REFERENCE,
        failed_evidence_digest=FAILED_WEIGHT_DIGEST,
        failed_evidence_released_at=FAILED_EVIDENCE_RELEASED_AT,
    )

    view = _resolve(
        read_port=_ReadPort(record),
        failure_mode="non_reproducible",
    )

    fields = dict(view.fields)
    assert fields["verification_status"] == "not_verifiable"
    assert fields["failed_evidence_reference"] == FAILED_WEIGHT_REFERENCE
    assert fields["failed_evidence_digest"] == FAILED_WEIGHT_DIGEST
    assert fields["failed_evidence_released_at"] == FAILED_EVIDENCE_RELEASED_AT


@pytest.mark.parametrize(
    ("failed_evidence_kind", "failed_reference"),
    [
        (
            "weight_variance_compatibility_receipt",
            "weight_variance_compatibility_receipt:"
            "55555555-5555-4555-8555-555555555555",
        ),
        (
            "variance_design_receipt",
            "variance_design_receipt:66666666-6666-4666-8666-666666666666",
        ),
    ],
)
def test_non_reproducible_evidence_kind_uses_its_typed_reference(
    failed_evidence_kind: str,
    failed_reference: str,
) -> None:
    record = _record(
        failed_evidence_kind=failed_evidence_kind,
        failure_mode="non_reproducible",
        failed_evidence_reference=failed_reference,
        failed_evidence_digest=FAILED_WEIGHT_DIGEST,
        failed_evidence_released_at=FAILED_EVIDENCE_RELEASED_AT,
    )
    view = _resolve(
        read_port=_ReadPort(record),
        failed_evidence_kind=failed_evidence_kind,
        failure_mode="non_reproducible",
    )
    assert dict(view.fields)["failed_evidence_reference"] == failed_reference


def test_missing_and_non_reproducible_modes_fail_closed_on_incoherent_evidence() -> None:
    with pytest.raises(ValueError, match="must be absent"):
        _record(
            failed_evidence_reference=FAILED_WEIGHT_REFERENCE,
            failed_evidence_digest=FAILED_WEIGHT_DIGEST,
        )
    with pytest.raises(ValueError, match="required"):
        _record(failure_mode="non_reproducible")
    with pytest.raises(ValueError, match="failed_evidence_reference"):
        _record(
            failure_mode="non_reproducible",
            failed_evidence_reference=(
                "variance_design_receipt:22222222-2222-4222-8222-222222222222"
            ),
            failed_evidence_digest=FAILED_WEIGHT_DIGEST,
            failed_evidence_released_at=FAILED_EVIDENCE_RELEASED_AT,
        )


def test_reason_and_attempt_evidence_are_strict_and_non_aliasing() -> None:
    with pytest.raises(ValueError, match="failed_evidence_kind"):
        _record(failed_evidence_kind="point_weight")
    with pytest.raises(ValueError, match="failure_mode"):
        _record(failure_mode="unknown")
    with pytest.raises(ValueError, match="verification_attempt_reference"):
        _record(verification_attempt_reference="verification-attempt-v1")
    with pytest.raises(ValueError, match="verification_attempt_digest"):
        _record(verification_attempt_digest="not-a-digest")
    with pytest.raises(ValueError, match="must be distinct"):
        _record(verification_attempt_digest=RESULT_DIGEST)


def test_evaluation_must_precede_release() -> None:
    with pytest.raises(ValueError, match="evaluated_at"):
        _record(
            evaluated_at=datetime(2026, 9, 17, 6, 6, tzinfo=timezone.utc),
            verification_attempt_released_at=datetime(
                2026, 9, 17, 6, 6, tzinfo=timezone.utc
            ),
            released_at=RELEASED_AT,
        )


def test_authorization_denial_happens_before_owner_resolution() -> None:
    port = _ReadPort(_record())
    with pytest.raises(AuthorizationDeniedError):
        _resolve(read_port=port, policy=_policy(purpose_code="audit_review"))
    assert port.calls == []


def test_missing_noncanonical_or_mismatched_owner_outcome_fails_closed() -> None:
    with pytest.raises(ValidationResultNonVerifiabilityNotFound):
        _resolve(read_port=_ReadPort(None))
    with pytest.raises(ValidationResultNonVerifiabilityIntegrityError):
        _resolve(read_port=_ReadPort(object()))
    with pytest.raises(ValidationResultNonVerifiabilityIntegrityError):
        _resolve(read_port=_ReadPort(_record(result_digest="a" * 64)))


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
    with pytest.raises(ValidationResultNonVerifiabilityIntegrityError):
        _resolve(
            read_port=port,
            used_at=datetime(2026, 9, 17, 6, 4, tzinfo=timezone.utc),
        )
    assert len(port.calls) == 1


def test_record_and_view_are_immutable_and_public_view_construction_is_blocked() -> None:
    record = _record()
    with pytest.raises(AttributeError):
        object.__setattr__(record, "failure_mode", "non_reproducible")

    view = _resolve(read_port=_ReadPort(record))
    with pytest.raises(AttributeError):
        object.__setattr__(view, "fields", ())
    with pytest.raises(TypeError):
        ValidationResultNonVerifiabilityView(
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            fields=(),
        )


def test_cross_tenant_owner_outcome_is_rejected() -> None:
    with pytest.raises(ValidationResultNonVerifiabilityIntegrityError):
        _resolve(read_port=_ReadPort(_record(tenant_record_id=OTHER_TENANT)))
