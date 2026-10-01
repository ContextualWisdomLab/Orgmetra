"""Regression coverage for canonical calibration-benchmark owner structure."""

from __future__ import annotations

from datetime import datetime, timezone
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
OWNER_REFERENCE = "released_owner_contract:22222222-2222-4222-8222-222222222222"
BENCHMARK_DIGEST = "1" * 64
OWNER_DIGEST = "2" * 64
REFERENCE_AT = datetime(2026, 6, 30, tzinfo=timezone.utc)
OWNER_RELEASED_AT = datetime(2026, 7, 1, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 7, 15, tzinfo=timezone.utc)
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
    """Return configured owner evidence without normalizing tuple structure."""

    def __init__(self, result: object) -> None:
        self.result = result

    def read_calibration_benchmark_authority(self, **_: object) -> object:
        """Return the configured raw owner result."""
        return self.result


def _record() -> CalibrationBenchmarkAuthorityRecord:
    """Build one current canonical calibration-benchmark owner record."""
    return CalibrationBenchmarkAuthorityRecord(
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        benchmark_receipt_reference=BENCHMARK_REFERENCE,
        benchmark_receipt_version=4,
        benchmark_receipt_digest=BENCHMARK_DIGEST,
        benchmark_owner_contract_reference=OWNER_REFERENCE,
        benchmark_owner_contract_version=3,
        benchmark_owner_contract_digest=OWNER_DIGEST,
        benchmark_reference_at=REFERENCE_AT,
        benchmark_receipt_released_at=RELEASED_AT,
        owner_contract_released_at=OWNER_RELEASED_AT,
    )


def _resolve(read_port: object) -> object:
    """Resolve canonical coordinates through a supplied raw owner port."""
    principal = ValidationPrincipal(
        tenant_record_id=TENANT,
        actor_reference="person:validation-analyst-1",
        granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
    )
    policy = PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="calibration-benchmark-authority-read-v1",
        resource_kind="calibration_benchmark_authority",
        purpose_code="selection_validity_analysis",
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=READ_FIELDS,
    )
    return resolve_calibration_benchmark_authority(
        principal=principal,
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        benchmark_receipt_reference=BENCHMARK_REFERENCE,
        benchmark_receipt_version=4,
        benchmark_receipt_digest=BENCHMARK_DIGEST,
        benchmark_owner_contract_reference=OWNER_REFERENCE,
        benchmark_owner_contract_version=3,
        benchmark_owner_contract_digest=OWNER_DIGEST,
        benchmark_reference_at=REFERENCE_AT,
        used_at=USED_AT,
        purpose_code="selection_validity_analysis",
        policy=policy,
        read_port=read_port,
    )


def test_owner_port_cannot_append_hidden_tuple_fields_to_exact_benchmark_record() -> None:
    """Reject exact-typed evidence with coordinates outside the canonical tuple."""
    valid = _record()
    forged = tuple.__new__(
        CalibrationBenchmarkAuthorityRecord,
        (*tuple(valid), "hidden-unreviewed-owner-coordinate"),
    )

    with pytest.raises(CalibrationBenchmarkAuthorityIntegrityError):
        _resolve(_ReadPort(forged))


def test_malformed_exact_benchmark_record_maps_to_integrity_error() -> None:
    """Map truncated exact-typed evidence to the domain integrity boundary."""
    valid = _record()
    forged = tuple.__new__(CalibrationBenchmarkAuthorityRecord, tuple(valid)[:-1])

    with pytest.raises(CalibrationBenchmarkAuthorityIntegrityError):
        _resolve(_ReadPort(forged))
