"""Fail closed when released calibration benchmark evidence has been superseded."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.benchmark_authority import (
    CalibrationBenchmarkAuthorityIntegrityError,
    CalibrationBenchmarkAuthorityRecord,
    resolve_calibration_benchmark_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
BENCHMARK_REFERENCE = "calibration_benchmark_receipt:11111111-1111-4111-8111-111111111111"
SUCCESSOR_REFERENCE = "calibration_benchmark_receipt:33333333-3333-4333-8333-333333333333"
OWNER_CONTRACT_REFERENCE = "released_owner_contract:22222222-2222-4222-8222-222222222222"
BENCHMARK_DIGEST = "1" * 64
SUCCESSOR_DIGEST = "3" * 64
OWNER_CONTRACT_DIGEST = "2" * 64
BENCHMARK_REFERENCE_AT = datetime(2026, 6, 30, tzinfo=timezone.utc)
BENCHMARK_RELEASED_AT = datetime(2026, 7, 15, tzinfo=timezone.utc)
OWNER_CONTRACT_RELEASED_AT = datetime(2026, 7, 1, tzinfo=timezone.utc)
USED_AT = datetime(2026, 9, 17, tzinfo=timezone.utc)
READ_FIELDS = frozenset(
    {
        "benchmark_receipt_reference",
        "benchmark_receipt_version",
        "benchmark_receipt_digest",
        "benchmark_owner_contract_reference",
        "benchmark_owner_contract_version",
        "benchmark_owner_contract_digest",
        "benchmark_reference_at",
        "benchmark_receipt_released_at",
        "owner_contract_released_at",
    }
)


class _ReadPort:
    """Return one configured owner record through the canonical benchmark read shape."""

    def __init__(self, record: CalibrationBenchmarkAuthorityRecord) -> None:
        self.record = record

    def read_calibration_benchmark_authority(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        benchmark_receipt_reference: str,
        benchmark_receipt_version: int,
        benchmark_receipt_digest: str,
        benchmark_owner_contract_reference: str,
        benchmark_owner_contract_version: int,
        benchmark_owner_contract_digest: str,
        benchmark_reference_at: datetime,
    ) -> CalibrationBenchmarkAuthorityRecord:
        """Return the owner-resolved record; resolver verifies every requested coordinate."""
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
        policy_version_code="calibration-benchmark-authority-read-v1",
        resource_kind="calibration_benchmark_authority",
        purpose_code="selection_validity_analysis",
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=READ_FIELDS,
    )


def _record(
    *,
    superseded_at: datetime | None,
    successor_reference: str | None,
    successor_version: int | None,
    successor_digest: str | None,
    successor_released_at: datetime | None,
) -> CalibrationBenchmarkAuthorityRecord:
    return CalibrationBenchmarkAuthorityRecord(
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        benchmark_receipt_reference=BENCHMARK_REFERENCE,
        benchmark_receipt_version=4,
        benchmark_receipt_digest=BENCHMARK_DIGEST,
        benchmark_owner_contract_reference=OWNER_CONTRACT_REFERENCE,
        benchmark_owner_contract_version=3,
        benchmark_owner_contract_digest=OWNER_CONTRACT_DIGEST,
        benchmark_reference_at=BENCHMARK_REFERENCE_AT,
        benchmark_receipt_released_at=BENCHMARK_RELEASED_AT,
        owner_contract_released_at=OWNER_CONTRACT_RELEASED_AT,
        benchmark_receipt_superseded_at=superseded_at,
        successor_benchmark_receipt_reference=successor_reference,
        successor_benchmark_receipt_version=successor_version,
        successor_benchmark_receipt_digest=successor_digest,
        successor_benchmark_receipt_released_at=successor_released_at,
    )


def _resolve(record: CalibrationBenchmarkAuthorityRecord, *, used_at: datetime = USED_AT):
    return resolve_calibration_benchmark_authority(
        principal=_principal(),
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        benchmark_receipt_reference=BENCHMARK_REFERENCE,
        benchmark_receipt_version=4,
        benchmark_receipt_digest=BENCHMARK_DIGEST,
        benchmark_owner_contract_reference=OWNER_CONTRACT_REFERENCE,
        benchmark_owner_contract_version=3,
        benchmark_owner_contract_digest=OWNER_CONTRACT_DIGEST,
        benchmark_reference_at=BENCHMARK_REFERENCE_AT,
        used_at=used_at,
        purpose_code="selection_validity_analysis",
        policy=_policy(),
        read_port=_ReadPort(record),
    )


def test_historical_use_before_supersession_remains_verifiable_without_leaking_lineage() -> None:
    superseded_at = USED_AT + timedelta(days=1)
    view = _resolve(
        _record(
            superseded_at=superseded_at,
            successor_reference=SUCCESSOR_REFERENCE,
            successor_version=5,
            successor_digest=SUCCESSOR_DIGEST,
            successor_released_at=USED_AT + timedelta(hours=12),
        )
    )

    fields = dict(view.fields)
    assert fields["benchmark_receipt_reference"] == BENCHMARK_REFERENCE
    assert "benchmark_receipt_superseded_at" not in fields
    assert "successor_benchmark_receipt_reference" not in fields
    assert "successor_benchmark_receipt_released_at" not in fields


def test_benchmark_receipt_cannot_predate_its_released_owner_contract() -> None:
    with pytest.raises(ValueError, match="owner contract must be released no later than benchmark receipt"):
        CalibrationBenchmarkAuthorityRecord(
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            benchmark_receipt_reference=BENCHMARK_REFERENCE,
            benchmark_receipt_version=4,
            benchmark_receipt_digest=BENCHMARK_DIGEST,
            benchmark_owner_contract_reference=OWNER_CONTRACT_REFERENCE,
            benchmark_owner_contract_version=3,
            benchmark_owner_contract_digest=OWNER_CONTRACT_DIGEST,
            benchmark_reference_at=BENCHMARK_REFERENCE_AT,
            benchmark_receipt_released_at=BENCHMARK_RELEASED_AT,
            owner_contract_released_at=BENCHMARK_RELEASED_AT + timedelta(seconds=1),
        )


def test_benchmark_superseded_by_scientific_use_is_not_authoritative() -> None:
    record = _record(
        superseded_at=USED_AT,
        successor_reference=SUCCESSOR_REFERENCE,
        successor_version=5,
        successor_digest=SUCCESSOR_DIGEST,
        successor_released_at=USED_AT - timedelta(hours=1),
    )

    with pytest.raises(CalibrationBenchmarkAuthorityIntegrityError):
        _resolve(record)


@pytest.mark.parametrize(
    (
        "superseded_at",
        "successor_reference",
        "successor_version",
        "successor_digest",
        "successor_released_at",
    ),
    [
        (USED_AT, None, 5, SUCCESSOR_DIGEST, USED_AT),
        (None, SUCCESSOR_REFERENCE, 5, SUCCESSOR_DIGEST, USED_AT),
        (USED_AT, SUCCESSOR_REFERENCE, 4, SUCCESSOR_DIGEST, USED_AT),
        (USED_AT, SUCCESSOR_REFERENCE, 5, BENCHMARK_DIGEST, USED_AT),
        (
            BENCHMARK_RELEASED_AT - timedelta(seconds=1),
            SUCCESSOR_REFERENCE,
            5,
            SUCCESSOR_DIGEST,
            BENCHMARK_RELEASED_AT - timedelta(seconds=1),
        ),
        (
            USED_AT,
            SUCCESSOR_REFERENCE,
            5,
            SUCCESSOR_DIGEST,
            USED_AT + timedelta(seconds=1),
        ),
        (
            USED_AT,
            SUCCESSOR_REFERENCE,
            5,
            SUCCESSOR_DIGEST,
            BENCHMARK_RELEASED_AT,
        ),
    ],
)
def test_owner_record_rejects_incomplete_or_non_append_only_supersession_lineage(
    superseded_at: datetime | None,
    successor_reference: str | None,
    successor_version: int | None,
    successor_digest: str | None,
    successor_released_at: datetime | None,
) -> None:
    with pytest.raises(ValueError):
        _record(
            superseded_at=superseded_at,
            successor_reference=successor_reference,
            successor_version=successor_version,
            successor_digest=successor_digest,
            successor_released_at=successor_released_at,
        )
