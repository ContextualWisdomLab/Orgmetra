"""Currentness contract for released base/design-weight evidence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.base_weight_authority import (
    BaseWeightAuthorityIntegrityError,
    BaseWeightAuthorityRecord,
    _READ_FIELDS,
    resolve_base_weight_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000f1")
RELEASED = datetime(2026, 9, 17, 7, 30, tzinfo=timezone.utc)
CUTOVER = datetime(2026, 9, 18, 7, 30, tzinfo=timezone.utc)


class _ReadPort:
    def __init__(self, record: BaseWeightAuthorityRecord) -> None:
        self.record = record

    def read_base_weight_authority(self, **_: object) -> BaseWeightAuthorityRecord:
        return self.record


def _record(**overrides: object) -> BaseWeightAuthorityRecord:
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "validity_study_id": STUDY,
        "base_weight_evidence_receipt_reference": "base_weight_evidence_receipt:11111111-1111-4111-8111-111111111111",
        "base_weight_evidence_receipt_digest": "1" * 64,
        "evidence_version": 1,
        "source_universe_receipt_reference": "source_universe_receipt:22222222-2222-4222-8222-222222222222",
        "source_universe_receipt_version": 4,
        "source_universe_receipt_digest": "2" * 64,
        "source_universe_released_at": datetime(2026, 9, 17, 6, 0, tzinfo=timezone.utc),
        "sampling_design_receipt_reference": "sampling_design_receipt:33333333-3333-4333-8333-333333333333",
        "sampling_design_receipt_version": 3,
        "sampling_design_receipt_digest": "3" * 64,
        "sampling_design_released_at": datetime(2026, 9, 17, 6, 30, tzinfo=timezone.utc),
        "sampled_occurrence_set_digest": "4" * 64,
        "selection_probability_set_digest": "5" * 64,
        "selection_stage_count": 2,
        "base_weight_method_code": "inverse_inclusion_probability",
        "base_weight_method_version": 1,
        "base_weight_artifact_digest": "6" * 64,
        "constructed_at": datetime(2026, 9, 17, 7, 0, tzinfo=timezone.utc),
        "owner_contract_reference": "released_owner_contract:44444444-4444-4444-8444-444444444444",
        "owner_contract_version": 6,
        "owner_contract_digest": "7" * 64,
        "owner_contract_released_at": datetime(2026, 9, 17, 6, 45, tzinfo=timezone.utc),
        "released_at": RELEASED,
        "superseded_at": CUTOVER,
    }
    values.update(overrides)
    return BaseWeightAuthorityRecord(**values)


def _resolve(record: BaseWeightAuthorityRecord, *, used_at: datetime) -> None:
    values = dict(record.fields)
    for owner_resolved_field in (
        "source_universe_released_at",
        "sampling_design_released_at",
        "owner_contract_released_at",
    ):
        values.pop(owner_resolved_field)
    resolve_base_weight_authority(
        principal=ValidationPrincipal(
            tenant_record_id=TENANT,
            actor_reference="person:validation-analyst-1",
            granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
        ),
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        used_at=used_at,
        purpose_code="selection_validity_analysis",
        policy=PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="base-weight-authority-read-v1",
            resource_kind="base_weight_authority",
            purpose_code="selection_validity_analysis",
            operation_code="read",
            required_scope_code="orgmetra.workforce_validation.read",
            permitted_fields=_READ_FIELDS,
        ),
        read_port=_ReadPort(record),
        **values,
    )


def test_supersession_cutover_is_owner_resolved_and_half_open() -> None:
    record = _record()
    _resolve(record, used_at=CUTOVER - timedelta(microseconds=1))

    with pytest.raises(BaseWeightAuthorityIntegrityError, match="superseded"):
        _resolve(record, used_at=CUTOVER)


def test_superseded_at_requires_timezone_and_post_release_cutover() -> None:
    with pytest.raises(ValueError):
        _record(superseded_at=datetime(2026, 9, 18, 7, 30))

    with pytest.raises(ValueError, match="later than released_at"):
        _record(superseded_at=RELEASED)
