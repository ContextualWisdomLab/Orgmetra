"""RED contract for owner-resolved non-verifiability currentness."""

from __future__ import annotations

from datetime import datetime, timezone
from inspect import signature
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.result_nonverifiability import (
    ValidationResultNonVerifiabilityIntegrityError,
    ValidationResultNonVerifiabilityReadPort,
    ValidationResultNonVerifiabilityRecord,
    resolve_validation_result_nonverifiability,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
RESULT_REFERENCE = "validation_analysis_result:11111111-1111-4111-8111-111111111111"
ATTEMPT_REFERENCE = (
    "validation_evidence_verification_attempt:33333333-3333-4333-8333-333333333333"
)
OWNER_REFERENCE = "released_owner_contract:44444444-4444-4444-8444-444444444444"
RESULT_DIGEST = "1" * 64
ATTEMPT_DIGEST = "3" * 64
OWNER_DIGEST = "4" * 64
OWNER_RELEASED_AT = datetime(2026, 9, 17, 5, 55, tzinfo=timezone.utc)
EVALUATED_AT = datetime(2026, 9, 17, 6, 0, tzinfo=timezone.utc)
ATTEMPT_RELEASED_AT = datetime(2026, 9, 17, 6, 2, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 17, 6, 5, tzinfo=timezone.utc)
SUPERSEDED_AT = datetime(2026, 9, 17, 6, 20, tzinfo=timezone.utc)
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
    """Return one canonical owner record."""

    def __init__(self, record: ValidationResultNonVerifiabilityRecord) -> None:
        self.record = record

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
    ) -> ValidationResultNonVerifiabilityRecord:
        return self.record


def _record(*, superseded_at: datetime | None = SUPERSEDED_AT) -> ValidationResultNonVerifiabilityRecord:
    return ValidationResultNonVerifiabilityRecord(
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        result_reference=RESULT_REFERENCE,
        result_digest=RESULT_DIGEST,
        failed_evidence_kind="analysis_weight_receipt",
        failure_mode="missing",
        failed_evidence_reference=None,
        failed_evidence_digest=None,
        verification_attempt_reference=ATTEMPT_REFERENCE,
        verification_attempt_digest=ATTEMPT_DIGEST,
        verification_attempt_released_at=ATTEMPT_RELEASED_AT,
        owner_contract_reference=OWNER_REFERENCE,
        owner_contract_version=7,
        owner_contract_digest=OWNER_DIGEST,
        owner_contract_released_at=OWNER_RELEASED_AT,
        evaluated_at=EVALUATED_AT,
        released_at=RELEASED_AT,
        superseded_at=superseded_at,
    )


def _resolve(*, record: ValidationResultNonVerifiabilityRecord, used_at: datetime):
    return resolve_validation_result_nonverifiability(
        principal=ValidationPrincipal(
            tenant_record_id=TENANT,
            actor_reference="person:validation-analyst-1",
            granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
        ),
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        result_reference=RESULT_REFERENCE,
        result_digest=RESULT_DIGEST,
        failed_evidence_kind="analysis_weight_receipt",
        failure_mode="missing",
        owner_contract_reference=OWNER_REFERENCE,
        owner_contract_version=7,
        owner_contract_digest=OWNER_DIGEST,
        used_at=used_at,
        purpose_code="selection_validity_analysis",
        policy=PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="validation-result-nonverifiability-read-v1",
            resource_kind="validation_result_nonverifiability",
            purpose_code="selection_validity_analysis",
            operation_code="read",
            required_scope_code="orgmetra.workforce_validation.read",
            permitted_fields=READ_FIELDS,
        ),
        read_port=_ReadPort(record),
    )


def test_nonverifiability_cutover_is_owner_evidence_not_caller_coordinate() -> None:
    assert "superseded_at" not in signature(resolve_validation_result_nonverifiability).parameters
    assert (
        "superseded_at"
        not in signature(
            ValidationResultNonVerifiabilityReadPort.read_validation_result_nonverifiability
        ).parameters
    )


def test_nonverifiability_is_valid_only_before_owner_resolved_cutover() -> None:
    record = _record()

    historical = _resolve(
        record=record,
        used_at=datetime(2026, 9, 17, 6, 19, 59, tzinfo=timezone.utc),
    )
    assert dict(historical.fields)["superseded_at"] == SUPERSEDED_AT

    with pytest.raises(
        ValidationResultNonVerifiabilityIntegrityError,
        match="supersession instant",
    ):
        _resolve(record=record, used_at=SUPERSEDED_AT)


def test_nonverifiability_cutover_must_follow_release_and_be_timezone_aware() -> None:
    with pytest.raises(ValueError, match="later than"):
        _record(superseded_at=RELEASED_AT)
    with pytest.raises(ValueError, match="timezone-aware"):
        _record(superseded_at=datetime(2026, 9, 17, 6, 20))
