"""Require an immutable successor verification attempt behind negative-outcome cutover."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.result_nonverifiability_supersession_authority import (
    ValidationResultNonVerifiabilitySupersessionAuthorityIntegrityError,
    ValidationResultNonVerifiabilitySupersessionAuthorityRecord,
    resolve_validation_result_nonverifiability_supersession_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
RESULT_REFERENCE = "validation_analysis_result:11111111-1111-4111-8111-111111111111"
OWNER_CONTRACT_REFERENCE = "released_owner_contract:22222222-2222-4222-8222-222222222222"
ATTEMPT_REFERENCE = "validation_evidence_verification_attempt:33333333-3333-4333-8333-333333333333"
SUCCESSOR_ATTEMPT_REFERENCE = "validation_evidence_verification_attempt:44444444-4444-4444-8444-444444444444"
RESULT_DIGEST = "1" * 64
OWNER_CONTRACT_DIGEST = "2" * 64
ATTEMPT_DIGEST = "3" * 64
SUCCESSOR_ATTEMPT_DIGEST = "4" * 64
OWNER_CONTRACT_RELEASED_AT = datetime(2026, 9, 1, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 18, 8, tzinfo=timezone.utc)
USED_AT = datetime(2026, 9, 18, 10, tzinfo=timezone.utc)
READ_FIELDS = frozenset(
    {
        "result_reference",
        "result_digest",
        "failed_evidence_kind",
        "failure_mode",
        "verification_attempt_reference",
        "verification_attempt_digest",
        "evidence_version",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "released_at",
        "superseded_at",
        "successor_target_result_reference",
        "successor_target_result_digest",
        "successor_verification_attempt_reference",
        "successor_verification_attempt_digest",
        "successor_verification_attempt_released_at",
    }
)


class _ReadPort:
    """Return one configured owner record through the negative-outcome successor shape."""

    def __init__(self, record: ValidationResultNonVerifiabilitySupersessionAuthorityRecord) -> None:
        self.record = record

    def read_validation_result_nonverifiability_supersession_authority(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        result_reference: str,
        result_digest: str,
        failed_evidence_kind: str,
        failure_mode: str,
        verification_attempt_reference: str,
        verification_attempt_digest: str,
        evidence_version: int,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
    ) -> ValidationResultNonVerifiabilitySupersessionAuthorityRecord:
        """Return owner evidence; the resolver verifies every caller-known coordinate."""
        return self.record


def _principal() -> ValidationPrincipal:
    """Return the canonical tenant-scoped workforce-validation principal."""
    return ValidationPrincipal(
        tenant_record_id=TENANT,
        actor_reference="person:validation-analyst-1",
        granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
    )


def _policy() -> PurposeBoundAccessPolicy:
    """Return the exact purpose-bound policy for negative-outcome successor evidence."""
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="validation-result-nonverifiability-supersession-read-v1",
        resource_kind="validation_result_nonverifiability_supersession_authority",
        purpose_code="selection_validity_analysis",
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=READ_FIELDS,
    )


def _record(
    *,
    superseded_at: datetime | None,
    successor_reference: str | None,
    successor_digest: str | None,
    successor_released_at: datetime | None,
) -> ValidationResultNonVerifiabilitySupersessionAuthorityRecord:
    """Build one canonical predecessor and optional same-result successor attempt."""
    has_successor = successor_reference is not None
    return ValidationResultNonVerifiabilitySupersessionAuthorityRecord(
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        result_reference=RESULT_REFERENCE,
        result_digest=RESULT_DIGEST,
        failed_evidence_kind="analysis_weight_receipt",
        failure_mode="missing",
        verification_attempt_reference=ATTEMPT_REFERENCE,
        verification_attempt_digest=ATTEMPT_DIGEST,
        evidence_version=1,
        owner_contract_reference=OWNER_CONTRACT_REFERENCE,
        owner_contract_version=3,
        owner_contract_digest=OWNER_CONTRACT_DIGEST,
        owner_contract_released_at=OWNER_CONTRACT_RELEASED_AT,
        released_at=RELEASED_AT,
        superseded_at=superseded_at,
        successor_target_result_reference=(RESULT_REFERENCE if has_successor else None),
        successor_target_result_digest=(RESULT_DIGEST if has_successor else None),
        successor_verification_attempt_reference=successor_reference,
        successor_verification_attempt_digest=successor_digest,
        successor_verification_attempt_released_at=successor_released_at,
    )


def _resolve(
    record: ValidationResultNonVerifiabilitySupersessionAuthorityRecord,
    *,
    used_at: datetime = USED_AT,
):
    """Resolve the canonical predecessor through its purpose-bound owner port."""
    return resolve_validation_result_nonverifiability_supersession_authority(
        principal=_principal(),
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        result_reference=RESULT_REFERENCE,
        result_digest=RESULT_DIGEST,
        failed_evidence_kind="analysis_weight_receipt",
        failure_mode="missing",
        verification_attempt_reference=ATTEMPT_REFERENCE,
        verification_attempt_digest=ATTEMPT_DIGEST,
        evidence_version=1,
        owner_contract_reference=OWNER_CONTRACT_REFERENCE,
        owner_contract_version=3,
        owner_contract_digest=OWNER_CONTRACT_DIGEST,
        used_at=used_at,
        purpose_code="selection_validity_analysis",
        policy=_policy(),
        read_port=_ReadPort(record),
    )


def test_historical_negative_outcome_hides_successor_attempt() -> None:
    """Keep historical negative evidence usable without leaking successor coordinates."""
    cutover = USED_AT + timedelta(hours=1)
    view = _resolve(
        _record(
            superseded_at=cutover,
            successor_reference=SUCCESSOR_ATTEMPT_REFERENCE,
            successor_digest=SUCCESSOR_ATTEMPT_DIGEST,
            successor_released_at=cutover,
        )
    )

    fields = dict(view.fields)
    assert fields["verification_attempt_reference"] == ATTEMPT_REFERENCE
    assert fields["failed_evidence_kind"] == "analysis_weight_receipt"
    assert "superseded_at" not in fields
    assert "successor_verification_attempt_reference" not in fields
    assert "successor_target_result_reference" not in fields


def test_negative_outcome_fails_closed_at_successor_cutover() -> None:
    """Reject use at the exact instant the successor verification attempt takes authority."""
    record = _record(
        superseded_at=USED_AT,
        successor_reference=SUCCESSOR_ATTEMPT_REFERENCE,
        successor_digest=SUCCESSOR_ATTEMPT_DIGEST,
        successor_released_at=USED_AT,
    )

    with pytest.raises(ValidationResultNonVerifiabilitySupersessionAuthorityIntegrityError):
        _resolve(record)


@pytest.mark.parametrize(
    ("superseded_at", "successor_reference", "successor_digest", "successor_released_at"),
    [
        (USED_AT, None, SUCCESSOR_ATTEMPT_DIGEST, USED_AT),
        (None, SUCCESSOR_ATTEMPT_REFERENCE, SUCCESSOR_ATTEMPT_DIGEST, USED_AT),
        (USED_AT, ATTEMPT_REFERENCE, SUCCESSOR_ATTEMPT_DIGEST, USED_AT),
        (USED_AT, SUCCESSOR_ATTEMPT_REFERENCE, ATTEMPT_DIGEST, USED_AT),
        (USED_AT, SUCCESSOR_ATTEMPT_REFERENCE, SUCCESSOR_ATTEMPT_DIGEST, USED_AT - timedelta(seconds=1)),
        (USED_AT, SUCCESSOR_ATTEMPT_REFERENCE, SUCCESSOR_ATTEMPT_DIGEST, USED_AT + timedelta(seconds=1)),
        (RELEASED_AT, SUCCESSOR_ATTEMPT_REFERENCE, SUCCESSOR_ATTEMPT_DIGEST, RELEASED_AT),
    ],
)
def test_owner_record_rejects_incomplete_or_non_atomic_successor_attempt(
    superseded_at: datetime | None,
    successor_reference: str | None,
    successor_digest: str | None,
    successor_released_at: datetime | None,
) -> None:
    """Require one complete, new, release-at-cutover successor verification attempt."""
    with pytest.raises(ValueError):
        _record(
            superseded_at=superseded_at,
            successor_reference=successor_reference,
            successor_digest=successor_digest,
            successor_released_at=successor_released_at,
        )
