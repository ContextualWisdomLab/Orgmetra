"""Fail closed when released final analysis-weight evidence has been superseded."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.final_weight_supersession_authority import (
    FinalWeightSupersessionAuthorityIntegrityError,
    FinalWeightSupersessionAuthorityRecord,
    resolve_final_weight_supersession_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
RECEIPT_REFERENCE = "analysis_weight_receipt:11111111-1111-4111-8111-111111111111"
SUCCESSOR_REFERENCE = "analysis_weight_receipt:33333333-3333-4333-8333-333333333333"
OWNER_CONTRACT_REFERENCE = "released_owner_contract:22222222-2222-4222-8222-222222222222"
RECEIPT_DIGEST = "1" * 64
SUCCESSOR_DIGEST = "3" * 64
OWNER_CONTRACT_DIGEST = "2" * 64
RELEASED_AT = datetime(2026, 7, 15, tzinfo=timezone.utc)
OWNER_CONTRACT_RELEASED_AT = datetime(2026, 7, 1, tzinfo=timezone.utc)
USED_AT = datetime(2026, 9, 17, tzinfo=timezone.utc)
READ_FIELDS = frozenset(
    {
        "analysis_weight_receipt_reference",
        "analysis_weight_receipt_digest",
        "evidence_version",
        "correction_sequence",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "released_at",
    }
)


class _ReadPort:
    """Return one configured owner record through the canonical supersession read shape."""

    def __init__(self, record: FinalWeightSupersessionAuthorityRecord) -> None:
        self.record = record

    def read_final_weight_supersession_authority(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        analysis_weight_receipt_reference: str,
        analysis_weight_receipt_digest: str,
        evidence_version: int,
        correction_sequence: int,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
    ) -> FinalWeightSupersessionAuthorityRecord:
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
        policy_version_code="final-weight-supersession-authority-read-v1",
        resource_kind="final_weight_supersession_authority",
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
) -> FinalWeightSupersessionAuthorityRecord:
    return FinalWeightSupersessionAuthorityRecord(
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        analysis_weight_receipt_reference=RECEIPT_REFERENCE,
        analysis_weight_receipt_digest=RECEIPT_DIGEST,
        evidence_version=1,
        correction_sequence=2,
        owner_contract_reference=OWNER_CONTRACT_REFERENCE,
        owner_contract_version=3,
        owner_contract_digest=OWNER_CONTRACT_DIGEST,
        owner_contract_released_at=OWNER_CONTRACT_RELEASED_AT,
        released_at=RELEASED_AT,
        superseded_at=superseded_at,
        successor_analysis_weight_receipt_reference=successor_reference,
        successor_correction_sequence=successor_correction_sequence,
        successor_analysis_weight_receipt_digest=successor_digest,
        successor_released_at=successor_released_at,
    )


def _resolve(
    record: FinalWeightSupersessionAuthorityRecord,
    *,
    used_at: datetime = USED_AT,
):
    return resolve_final_weight_supersession_authority(
        principal=_principal(),
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        analysis_weight_receipt_reference=RECEIPT_REFERENCE,
        analysis_weight_receipt_digest=RECEIPT_DIGEST,
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


def test_historical_use_before_supersession_remains_verifiable_without_leaking_successor() -> None:
    superseded_at = USED_AT + timedelta(days=1)
    view = _resolve(
        _record(
            superseded_at=superseded_at,
            successor_reference=SUCCESSOR_REFERENCE,
            successor_correction_sequence=3,
            successor_digest=SUCCESSOR_DIGEST,
            successor_released_at=USED_AT + timedelta(hours=12),
        )
    )

    fields = dict(view.fields)
    assert fields["analysis_weight_receipt_reference"] == RECEIPT_REFERENCE
    assert fields["correction_sequence"] == 2
    assert "superseded_at" not in fields
    assert "successor_analysis_weight_receipt_reference" not in fields
    assert "successor_released_at" not in fields


def test_superseded_final_weight_is_not_authoritative_at_or_after_cutover() -> None:
    record = _record(
        superseded_at=USED_AT,
        successor_reference=SUCCESSOR_REFERENCE,
        successor_correction_sequence=3,
        successor_digest=SUCCESSOR_DIGEST,
        successor_released_at=USED_AT - timedelta(hours=1),
    )

    with pytest.raises(FinalWeightSupersessionAuthorityIntegrityError):
        _resolve(record)


def test_owner_contract_cannot_be_released_after_final_weight_receipt() -> None:
    with pytest.raises(ValueError, match="owner contract must be released no later than final-weight receipt"):
        FinalWeightSupersessionAuthorityRecord(
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            analysis_weight_receipt_reference=RECEIPT_REFERENCE,
            analysis_weight_receipt_digest=RECEIPT_DIGEST,
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
        (USED_AT, RECEIPT_REFERENCE, 3, SUCCESSOR_DIGEST, USED_AT),
        (USED_AT, SUCCESSOR_REFERENCE, 2, SUCCESSOR_DIGEST, USED_AT),
        (USED_AT, SUCCESSOR_REFERENCE, 3, RECEIPT_DIGEST, USED_AT),
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
def test_owner_record_rejects_incomplete_or_non_append_only_supersession_lineage(
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
