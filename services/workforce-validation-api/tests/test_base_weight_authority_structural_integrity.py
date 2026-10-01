"""Regression coverage for canonical base-weight owner evidence structure."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.base_weight_authority import (
    BaseWeightAuthorityIntegrityError,
    BaseWeightAuthorityRecord,
    resolve_base_weight_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000f1")
BASE_RECEIPT_REFERENCE = "base_weight_evidence_receipt:11111111-1111-4111-8111-111111111111"
SOURCE_REFERENCE = "source_universe_receipt:22222222-2222-4222-8222-222222222222"
SAMPLING_REFERENCE = "sampling_design_receipt:33333333-3333-4333-8333-333333333333"
OWNER_REFERENCE = "released_owner_contract:44444444-4444-4444-8444-444444444444"
BASE_RECEIPT_DIGEST = "1" * 64
SOURCE_DIGEST = "2" * 64
SAMPLING_DIGEST = "3" * 64
SAMPLED_SET_DIGEST = "4" * 64
SELECTION_PROBABILITY_SET_DIGEST = "5" * 64
BASE_ARTIFACT_DIGEST = "6" * 64
OWNER_DIGEST = "7" * 64
SOURCE_RELEASED_AT = datetime(2026, 9, 17, 6, 0, tzinfo=timezone.utc)
SAMPLING_RELEASED_AT = datetime(2026, 9, 17, 6, 30, tzinfo=timezone.utc)
OWNER_CONTRACT_RELEASED_AT = datetime(2026, 9, 17, 6, 45, tzinfo=timezone.utc)
CONSTRUCTED_AT = datetime(2026, 9, 17, 7, 0, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 17, 7, 30, tzinfo=timezone.utc)
USED_AT = datetime(2026, 9, 17, 8, 0, tzinfo=timezone.utc)
READ_FIELDS = frozenset(
    {
        "base_weight_evidence_receipt_reference",
        "base_weight_evidence_receipt_digest",
        "evidence_version",
        "source_universe_receipt_reference",
        "source_universe_receipt_version",
        "source_universe_receipt_digest",
        "source_universe_released_at",
        "sampling_design_receipt_reference",
        "sampling_design_receipt_version",
        "sampling_design_receipt_digest",
        "sampling_design_released_at",
        "sampled_occurrence_set_digest",
        "selection_probability_set_digest",
        "selection_stage_count",
        "base_weight_method_code",
        "base_weight_method_version",
        "base_weight_artifact_digest",
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
    """Return configured owner evidence without normalizing its tuple structure."""

    def __init__(self, result: object) -> None:
        self.result = result

    def read_base_weight_authority(self, **_: object) -> object:
        """Return the configured raw owner result."""
        return self.result


def _record() -> BaseWeightAuthorityRecord:
    """Build one valid canonical base-weight authority record."""
    return BaseWeightAuthorityRecord(
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        base_weight_evidence_receipt_reference=BASE_RECEIPT_REFERENCE,
        base_weight_evidence_receipt_digest=BASE_RECEIPT_DIGEST,
        evidence_version=1,
        source_universe_receipt_reference=SOURCE_REFERENCE,
        source_universe_receipt_version=4,
        source_universe_receipt_digest=SOURCE_DIGEST,
        source_universe_released_at=SOURCE_RELEASED_AT,
        sampling_design_receipt_reference=SAMPLING_REFERENCE,
        sampling_design_receipt_version=3,
        sampling_design_receipt_digest=SAMPLING_DIGEST,
        sampling_design_released_at=SAMPLING_RELEASED_AT,
        sampled_occurrence_set_digest=SAMPLED_SET_DIGEST,
        selection_probability_set_digest=SELECTION_PROBABILITY_SET_DIGEST,
        selection_stage_count=2,
        base_weight_method_code="inverse_inclusion_probability",
        base_weight_method_version=1,
        base_weight_artifact_digest=BASE_ARTIFACT_DIGEST,
        constructed_at=CONSTRUCTED_AT,
        owner_contract_reference=OWNER_REFERENCE,
        owner_contract_version=6,
        owner_contract_digest=OWNER_DIGEST,
        owner_contract_released_at=OWNER_CONTRACT_RELEASED_AT,
        released_at=RELEASED_AT,
    )


def _resolve(read_port: object) -> object:
    """Resolve the canonical coordinates through a supplied raw owner port."""
    principal = ValidationPrincipal(
        tenant_record_id=TENANT,
        actor_reference="person:validation-analyst-1",
        granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
    )
    policy = PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="base-weight-authority-read-v1",
        resource_kind="base_weight_authority",
        purpose_code="selection_validity_analysis",
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=READ_FIELDS,
    )
    return resolve_base_weight_authority(
        principal=principal,
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        base_weight_evidence_receipt_reference=BASE_RECEIPT_REFERENCE,
        base_weight_evidence_receipt_digest=BASE_RECEIPT_DIGEST,
        evidence_version=1,
        source_universe_receipt_reference=SOURCE_REFERENCE,
        source_universe_receipt_version=4,
        source_universe_receipt_digest=SOURCE_DIGEST,
        sampling_design_receipt_reference=SAMPLING_REFERENCE,
        sampling_design_receipt_version=3,
        sampling_design_receipt_digest=SAMPLING_DIGEST,
        sampled_occurrence_set_digest=SAMPLED_SET_DIGEST,
        selection_probability_set_digest=SELECTION_PROBABILITY_SET_DIGEST,
        selection_stage_count=2,
        base_weight_method_code="inverse_inclusion_probability",
        base_weight_method_version=1,
        base_weight_artifact_digest=BASE_ARTIFACT_DIGEST,
        constructed_at=CONSTRUCTED_AT,
        owner_contract_reference=OWNER_REFERENCE,
        owner_contract_version=6,
        owner_contract_digest=OWNER_DIGEST,
        used_at=USED_AT,
        purpose_code="selection_validity_analysis",
        policy=policy,
        read_port=read_port,
    )


def test_owner_port_cannot_append_hidden_tuple_fields_to_exact_base_weight_record() -> None:
    """Reject exact-typed owner evidence with coordinates outside the canonical tuple."""
    valid = _record()
    forged = tuple.__new__(
        BaseWeightAuthorityRecord,
        (*tuple(valid), "hidden-unreviewed-owner-coordinate"),
    )

    with pytest.raises(BaseWeightAuthorityIntegrityError):
        _resolve(_ReadPort(forged))


def test_malformed_exact_base_weight_record_maps_to_integrity_error() -> None:
    """Map a truncated exact-typed owner tuple to the domain integrity boundary."""
    valid = _record()
    forged = tuple.__new__(BaseWeightAuthorityRecord, tuple(valid)[:-1])

    with pytest.raises(BaseWeightAuthorityIntegrityError):
        _resolve(_ReadPort(forged))
