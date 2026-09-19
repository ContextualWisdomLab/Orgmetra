"""Fail closed when a released validation result has been superseded."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.result_supersession_authority import (
    ValidationResultSupersessionAuthorityIntegrityError,
    ValidationResultSupersessionAuthorityRecord,
    resolve_validation_result_supersession_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
RESULT_REFERENCE = "validation_analysis_result:11111111-1111-4111-8111-111111111111"
SUCCESSOR_REFERENCE = "validation_analysis_result:33333333-3333-4333-8333-333333333333"
OWNER_CONTRACT_REFERENCE = "released_owner_contract:22222222-2222-4222-8222-222222222222"
RESULT_DIGEST = "1" * 64
SUCCESSOR_DIGEST = "3" * 64
OWNER_CONTRACT_DIGEST = "2" * 64
RELEASED_AT = datetime(2026, 9, 17, 10, tzinfo=timezone.utc)
OWNER_CONTRACT_RELEASED_AT = datetime(2026, 9, 1, tzinfo=timezone.utc)
USED_AT = datetime(2026, 9, 17, 12, tzinfo=timezone.utc)
READ_FIELDS = frozenset(
    {
        "result_reference",
        "result_digest",
        "evidence_version",
        "correction_sequence",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "released_at",
        "superseded_at",
        "successor_result_reference",
        "successor_correction_sequence",
        "successor_result_digest",
        "successor_released_at",
    }
)


class _ReadPort:
    """Return one configured owner record through the result supersession read shape."""

    def __init__(self, record: ValidationResultSupersessionAuthorityRecord) -> None:
        self.record = record

    def read_validation_result_supersession_authority(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        result_reference: str,
        result_digest: str,
        evidence_version: int,
        correction_sequence: int,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
    ) -> ValidationResultSupersessionAuthorityRecord:
        """Return owner evidence; resolver verifies every request coordinate."""
        return self.record


def _principal() -> ValidationPrincipal:
    return ValidationPrincipal(
        tenant_record_id=TENANT,
        actor_reference="person:validation-analyst-1",
        granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
    )


def _policy() -> PurposeBoundAccessPolicy:
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="validation-result-supersession-authority-read-v1",
        resource_kind="validation_result_supersession_authority",
        purpose_code="selection_validity_analysis",
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=READ_FIELDS,
    )


def _record(
    *,
    superseded_at: datetime | None,
    successor_reference: str | None,
    successor_correction_sequence: int | None,
    successor_digest: str | None,
    successor_released_at: datetime | None,
) -> ValidationResultSupersessionAuthorityRecord:
    return ValidationResultSupersessionAuthorityRecord(
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        result_reference=RESULT_REFERENCE,
        result_digest=RESULT_DIGEST,
        evidence_version=1,
        correction_sequence=2,
        owner_contract_reference=OWNER_CONTRACT_REFERENCE,
        owner_contract_version=3,
        owner_contract_digest=OWNER_CONTRACT_DIGEST,
        owner_contract_released_at=OWNER_CONTRACT_RELEASED_AT,
        released_at=RELEASED_AT,
        superseded_at=superseded_at,
        successor_result_reference=successor_reference,
        successor_correction_sequence=successor_correction_sequence,
        successor_result_digest=successor_digest,
        successor_released_at=successor_released_at,
    )


def _resolve(
    record: ValidationResultSupersessionAuthorityRecord,
    *,
    used_at: datetime = USED_AT,
):
    return resolve_validation_result_supersession_authority(
        principal=_principal(),
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        result_reference=RESULT_REFERENCE,
        result_digest=RESULT_DIGEST,
        evidence_version=1,
        correction_sequence=2,
        owner_contract_reference=OWNER_CONTRACT_REFERENCE,
        owner_contract_version=3,
        owner_contract_digest=OWNER_CONTRACT_DIGEST,
        used_at=used_at,
        purpose_code="selection_validity_analysis",
        policy=_policy(),
        read_port=_ReadPort(record),
    )


def test_historical_result_use_before_supersession_remains_verifiable_without_leaking_successor() -> None:
    view = _resolve(
        _record(
            superseded_at=USED_AT + timedelta(days=1),
            successor_reference=SUCCESSOR_REFERENCE,
            successor_correction_sequence=3,
            successor_digest=SUCCESSOR_DIGEST,
            successor_released_at=USED_AT + timedelta(days=1),
        )
    )

    fields = dict(view.fields)
    assert fields["result_reference"] == RESULT_REFERENCE
    assert fields["correction_sequence"] == 2
    assert "superseded_at" not in fields
    assert "successor_result_reference" not in fields
    assert "successor_released_at" not in fields


def test_superseded_result_is_not_authoritative_at_or_after_cutover() -> None:
    record = _record(
        superseded_at=USED_AT,
        successor_reference=SUCCESSOR_REFERENCE,
        successor_correction_sequence=3,
        successor_digest=SUCCESSOR_DIGEST,
        successor_released_at=USED_AT,
    )

    with pytest.raises(ValidationResultSupersessionAuthorityIntegrityError):
        _resolve(record)


def test_owner_contract_cannot_be_released_after_result() -> None:
    with pytest.raises(ValueError, match="owner contract must be released no later than validation result"):
        ValidationResultSupersessionAuthorityRecord(
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            result_reference=RESULT_REFERENCE,
            result_digest=RESULT_DIGEST,
            evidence_version=1,
            correction_sequence=2,
            owner_contract_reference=OWNER_CONTRACT_REFERENCE,
            owner_contract_version=3,
            owner_contract_digest=OWNER_CONTRACT_DIGEST,
            owner_contract_released_at=RELEASED_AT + timedelta(seconds=1),
            released_at=RELEASED_AT,
        )


@pytest.mark.parametrize(
    (
        "superseded_at",
        "successor_reference",
        "successor_correction_sequence",
        "successor_digest",
        "successor_released_at",
    ),
    [
        (USED_AT, None, 3, SUCCESSOR_DIGEST, USED_AT),
        (None, SUCCESSOR_REFERENCE, 3, SUCCESSOR_DIGEST, USED_AT),
        (USED_AT, RESULT_REFERENCE, 3, SUCCESSOR_DIGEST, USED_AT),
        (USED_AT, SUCCESSOR_REFERENCE, 2, SUCCESSOR_DIGEST, USED_AT),
        (USED_AT, SUCCESSOR_REFERENCE, 3, RESULT_DIGEST, USED_AT),
        (
            RELEASED_AT - timedelta(seconds=1),
            SUCCESSOR_REFERENCE,
            3,
            SUCCESSOR_DIGEST,
            RELEASED_AT - timedelta(seconds=1),
        ),
        (
            USED_AT,
            SUCCESSOR_REFERENCE,
            3,
            SUCCESSOR_DIGEST,
            USED_AT + timedelta(seconds=1),
        ),
        (
            USED_AT,
            SUCCESSOR_REFERENCE,
            3,
            SUCCESSOR_DIGEST,
            RELEASED_AT,
        ),
    ],
)
def test_owner_record_rejects_incomplete_or_non_append_only_result_supersession(
    superseded_at: datetime | None,
    successor_reference: str | None,
    successor_correction_sequence: int | None,
    successor_digest: str | None,
    successor_released_at: datetime | None,
) -> None:
    with pytest.raises(ValueError):
        _record(
            superseded_at=superseded_at,
            successor_reference=successor_reference,
            successor_correction_sequence=successor_correction_sequence,
            successor_digest=successor_digest,
            successor_released_at=successor_released_at,
        )
