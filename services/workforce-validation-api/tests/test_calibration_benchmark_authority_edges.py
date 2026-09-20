"""Branch-complete scalar edges for calibration benchmark authority."""

from datetime import datetime, timezone
from uuid import UUID

import pytest

from orgmetra_workforce_validation_api.benchmark_authority import (
    CalibrationBenchmarkAuthorityRecord,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
REFERENCE_AT = datetime(2026, 6, 30, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 7, 15, tzinfo=timezone.utc)


def _record(**overrides: object) -> CalibrationBenchmarkAuthorityRecord:
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "benchmark_receipt_reference": (
            "calibration_benchmark_receipt:11111111-1111-4111-8111-111111111111"
        ),
        "benchmark_receipt_version": 4,
        "benchmark_receipt_digest": "1" * 64,
        "benchmark_owner_contract_reference": (
            "released_owner_contract:22222222-2222-4222-8222-222222222222"
        ),
        "benchmark_owner_contract_version": 3,
        "benchmark_owner_contract_digest": "2" * 64,
        "benchmark_reference_at": REFERENCE_AT,
        "benchmark_receipt_released_at": RELEASED_AT,
        "owner_contract_released_at": RELEASED_AT,
    }
    values.update(overrides)
    return CalibrationBenchmarkAuthorityRecord(**values)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("benchmark_receipt_reference", object()),
        ("benchmark_receipt_reference", "not namespaced"),
        ("benchmark_owner_contract_reference", object()),
        ("benchmark_receipt_digest", object()),
        ("benchmark_owner_contract_digest", 7),
    ],
)
def test_scalar_type_and_reference_shape_edges_fail_closed(
    field_name: str, value: object
) -> None:
    with pytest.raises(ValueError):
        _record(**{field_name: value})
