"""Structural-integrity regressions for weight-eligibility owner evidence."""

from __future__ import annotations

from datetime import datetime, timezone
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
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
RECEIPT_REFERENCE = "weight_eligibility_receipt:11111111-1111-4111-8111-111111111111"
TARGET_POPULATION_REFERENCE = "analysis_target_population:workers-2026q3"
REFERENCE_DURATION_REFERENCE = "analysis_reference_duration:2026q3"
OWNER_CONTRACT_REFERENCE = "released_owner_contract:22222222-2222-4222-8222-222222222222"
RECEIPT_DIGEST = "1" * 64
TARGET_POPULATION_DIGEST = "2" * 64
REFERENCE_DURATION_DIGEST = "3" * 64
ELIGIBLE_CASE_SET_DIGEST = "4" * 64
WEIGHT_ARTIFACT_DIGEST = "5" * 64
OWNER_CONTRACT_DIGEST = "6" * 64
CONSTRUCTED_AT = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)
OWNER_CONTRACT_RELEASED_AT = datetime(2026, 9, 16, 12, 30, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 16, 13, 0, tzinfo=timezone.utc)
USED_AT = datetime(2026, 9, 17, tzinfo=timezone.utc)
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
    """Return configured owner evidence without normalizing tuple structure."""

    def __init__(self, result: object) -> None:
        self.result = result

    def read_weight_eligibility_authority(self, **_: object) -> object:
        """Return the configured raw owner result."""
        return self.result


def _record() -> WeightEligibilityAuthorityRecord:
    """Build one valid canonical weight-eligibility authority record."""
    return WeightEligibilityAuthorityRecord(
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        eligibility_receipt_reference=RECEIPT_REFERENCE,
        eligibility_receipt_digest=RECEIPT_DIGEST,
        evidence_version=1,
        weight_scope_code="longitudinal",
        target_population_reference=TARGET_POPULATION_REFERENCE,
        target_population_digest=TARGET_POPULATION_DIGEST,
        reference_duration_reference=REFERENCE_DURATION_REFERENCE,
        reference_duration_digest=REFERENCE_DURATION_DIGEST,
        eligible_case_set_digest=ELIGIBLE_CASE_SET_DIGEST,
        weight_artifact_digest=WEIGHT_ARTIFACT_DIGEST,
        constructed_at=CONSTRUCTED_AT,
        owner_contract_reference=OWNER_CONTRACT_REFERENCE,
        owner_contract_version=3,
        owner_contract_digest=OWNER_CONTRACT_DIGEST,
        owner_contract_released_at=OWNER_CONTRACT_RELEASED_AT,
        released_at=RELEASED_AT,
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
        policy_version_code="weight-eligibility-authority-read-v2",
        resource_kind="weight_eligibility_authority",
        purpose_code="selection_validity_analysis",
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=READ_FIELDS,
    )
    return resolve_weight_eligibility_authority(
        principal=principal,
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        eligibility_receipt_reference=RECEIPT_REFERENCE,
        eligibility_receipt_digest=RECEIPT_DIGEST,
        evidence_version=1,
        weight_scope_code="longitudinal",
        target_population_reference=TARGET_POPULATION_REFERENCE,
        target_population_digest=TARGET_POPULATION_DIGEST,
        reference_duration_reference=REFERENCE_DURATION_REFERENCE,
        reference_duration_digest=REFERENCE_DURATION_DIGEST,
        eligible_case_set_digest=ELIGIBLE_CASE_SET_DIGEST,
        weight_artifact_digest=WEIGHT_ARTIFACT_DIGEST,
        constructed_at=CONSTRUCTED_AT,
        owner_contract_reference=OWNER_CONTRACT_REFERENCE,
        owner_contract_version=3,
        owner_contract_digest=OWNER_CONTRACT_DIGEST,
        used_at=USED_AT,
        purpose_code="selection_validity_analysis",
        policy=policy,
        read_port=read_port,
    )


def test_owner_port_cannot_append_hidden_tuple_fields() -> None:
    """Reject exact-typed evidence with coordinates outside the canonical tuple."""
    canonical = _record()
    forged = tuple.__new__(
        WeightEligibilityAuthorityRecord,
        (*tuple(canonical), "hidden-unreviewed-owner-coordinate"),
    )

    with pytest.raises(WeightEligibilityAuthorityIntegrityError):
        _resolve(_ReadPort(forged))


def test_truncated_exact_typed_tuple_maps_to_integrity_error() -> None:
    """Map truncated exact-typed evidence to the domain integrity boundary."""
    canonical = _record()
    forged = tuple.__new__(WeightEligibilityAuthorityRecord, tuple(canonical)[:-1])

    with pytest.raises(WeightEligibilityAuthorityIntegrityError):
        _resolve(_ReadPort(forged))
