"""Chronology contract for released weight-eligibility authority."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from inspect import signature
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.weight_eligibility_authority import (
    WeightEligibilityAuthorityIntegrityError,
    WeightEligibilityAuthorityRecord,
    resolve_weight_eligibility_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000c1")
RECEIPT_REFERENCE = "weight_eligibility_receipt:eligibility-chronology-1"
TARGET_REFERENCE = "analysis_target_population:population-1"
DURATION_REFERENCE = "analysis_reference_duration:duration-1"
OWNER_REFERENCE = "released_owner_contract:weight-eligibility-v1"
RECEIPT_DIGEST = "1" * 64
TARGET_DIGEST = "2" * 64
DURATION_DIGEST = "3" * 64
CASE_SET_DIGEST = "4" * 64
ARTIFACT_DIGEST = "5" * 64
OWNER_DIGEST = "6" * 64
CONSTRUCTED_AT = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)
OWNER_RELEASED_AT = datetime(2026, 9, 16, 12, 30, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 16, 13, 0, tzinfo=timezone.utc)
SUPERSEDED_AT = datetime(2026, 9, 17, 13, 0, tzinfo=timezone.utc)
READ_FIELDS = frozenset(
    {
        "eligibility_receipt_reference",
        "eligibility_receipt_digest",
        "evidence_version",
        "weight_scope_code",
        "target_population_reference",
        "target_population_digest",
        "reference_duration_reference",
        "reference_duration_digest",
        "eligible_case_set_digest",
        "weight_artifact_digest",
        "constructed_at",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "released_at",
        "superseded_at",
    }
)


class _ReadPort:
    def __init__(self, record: WeightEligibilityAuthorityRecord) -> None:
        self.record = record

    def read_weight_eligibility_authority(self, **_: object) -> WeightEligibilityAuthorityRecord:
        return self.record


def _record(
    *,
    owner_contract_released_at: datetime = OWNER_RELEASED_AT,
    superseded_at: datetime | None = SUPERSEDED_AT,
) -> WeightEligibilityAuthorityRecord:
    return WeightEligibilityAuthorityRecord(
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        eligibility_receipt_reference=RECEIPT_REFERENCE,
        eligibility_receipt_digest=RECEIPT_DIGEST,
        evidence_version=1,
        weight_scope_code="longitudinal",
        target_population_reference=TARGET_REFERENCE,
        target_population_digest=TARGET_DIGEST,
        reference_duration_reference=DURATION_REFERENCE,
        reference_duration_digest=DURATION_DIGEST,
        eligible_case_set_digest=CASE_SET_DIGEST,
        weight_artifact_digest=ARTIFACT_DIGEST,
        constructed_at=CONSTRUCTED_AT,
        owner_contract_reference=OWNER_REFERENCE,
        owner_contract_version=1,
        owner_contract_digest=OWNER_DIGEST,
        owner_contract_released_at=owner_contract_released_at,
        released_at=RELEASED_AT,
        superseded_at=superseded_at,
    )


def _policy() -> PurposeBoundAccessPolicy:
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="weight-eligibility-chronology-v2",
        resource_kind="weight_eligibility_authority",
        purpose_code="selection_validity_analysis",
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=READ_FIELDS,
    )


def _resolve(*, used_at: datetime, record: WeightEligibilityAuthorityRecord) -> object:
    return resolve_weight_eligibility_authority(
        principal=ValidationPrincipal(
            tenant_record_id=TENANT,
            actor_reference="person:validation-analyst-1",
            granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
        ),
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        eligibility_receipt_reference=RECEIPT_REFERENCE,
        eligibility_receipt_digest=RECEIPT_DIGEST,
        evidence_version=1,
        weight_scope_code="longitudinal",
        target_population_reference=TARGET_REFERENCE,
        target_population_digest=TARGET_DIGEST,
        reference_duration_reference=DURATION_REFERENCE,
        reference_duration_digest=DURATION_DIGEST,
        eligible_case_set_digest=CASE_SET_DIGEST,
        weight_artifact_digest=ARTIFACT_DIGEST,
        constructed_at=CONSTRUCTED_AT,
        owner_contract_reference=OWNER_REFERENCE,
        owner_contract_version=1,
        owner_contract_digest=OWNER_DIGEST,
        used_at=used_at,
        purpose_code="selection_validity_analysis",
        policy=_policy(),
        read_port=_ReadPort(record),
    )


def test_chronology_is_owner_evidence_not_caller_input() -> None:
    parameters = signature(resolve_weight_eligibility_authority).parameters
    assert "owner_contract_released_at" not in parameters
    assert "superseded_at" not in parameters


def test_owner_contract_cannot_retroactively_authorize_eligibility() -> None:
    with pytest.raises(ValueError, match="owner contract"):
        _record(owner_contract_released_at=RELEASED_AT + timedelta(microseconds=1))


def test_historical_use_before_cutover_remains_reproducible() -> None:
    view = _resolve(used_at=SUPERSEDED_AT - timedelta(microseconds=1), record=_record())
    fields = dict(view.fields)
    assert fields["owner_contract_released_at"] == OWNER_RELEASED_AT
    assert fields["released_at"] == RELEASED_AT
    assert fields["superseded_at"] == SUPERSEDED_AT


def test_use_at_or_after_owner_cutover_fails_closed() -> None:
    for used_at in (SUPERSEDED_AT, SUPERSEDED_AT + timedelta(seconds=1)):
        with pytest.raises(WeightEligibilityAuthorityIntegrityError):
            _resolve(used_at=used_at, record=_record())


def test_non_positive_owner_authority_interval_is_rejected() -> None:
    for superseded_at in (RELEASED_AT, RELEASED_AT - timedelta(microseconds=1)):
        with pytest.raises(ValueError):
            _record(superseded_at=superseded_at)


def test_unsuperseded_owner_evidence_remains_current() -> None:
    _resolve(used_at=SUPERSEDED_AT + timedelta(days=30), record=_record(superseded_at=None))
