"""Regression coverage for canonical validation-result owner evidence structure."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.result_authority import (
    ValidationResultAuthorityIntegrityError,
    ValidationResultAuthorityRecord,
    resolve_validation_result_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
RESULT_REFERENCE = "validation_analysis_result:11111111-1111-4111-8111-111111111111"
COMPATIBILITY_REFERENCE = (
    "weight_variance_compatibility_receipt:22222222-2222-4222-8222-222222222222"
)
OWNER_REFERENCE = "released_owner_contract:33333333-3333-4333-8333-333333333333"
RESULT_DIGEST = "1" * 64
COMPATIBILITY_DIGEST = "2" * 64
ANALYSIS_WEIGHT_DIGEST = "3" * 64
VARIANCE_DIGEST = "4" * 64
OWNER_DIGEST = "5" * 64
OWNER_RELEASED_AT = datetime(2026, 9, 17, 4, 0, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 17, 5, 0, tzinfo=timezone.utc)
USED_AT = datetime(2026, 9, 17, 6, 0, tzinfo=timezone.utc)
READ_FIELDS = frozenset(
    {
        "result_reference",
        "result_digest",
        "compatibility_receipt_reference",
        "compatibility_receipt_digest",
        "analysis_weight_receipt_digest",
        "variance_design_receipt_digest",
        "verification_status",
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

    def read_validation_result_authority(self, **_: object) -> object:
        """Return the configured raw owner result."""
        return self.result


def _record() -> ValidationResultAuthorityRecord:
    """Build one valid canonical validation-result authority record."""
    return ValidationResultAuthorityRecord(
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        result_reference=RESULT_REFERENCE,
        result_digest=RESULT_DIGEST,
        compatibility_receipt_reference=COMPATIBILITY_REFERENCE,
        compatibility_receipt_digest=COMPATIBILITY_DIGEST,
        analysis_weight_receipt_digest=ANALYSIS_WEIGHT_DIGEST,
        variance_design_receipt_digest=VARIANCE_DIGEST,
        verification_status="verification_pending",
        owner_contract_reference=OWNER_REFERENCE,
        owner_contract_version=7,
        owner_contract_digest=OWNER_DIGEST,
        owner_contract_released_at=OWNER_RELEASED_AT,
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
        policy_version_code="validation-result-authority-read-v2",
        resource_kind="validation_result_authority",
        purpose_code="selection_validity_analysis",
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=READ_FIELDS,
    )
    return resolve_validation_result_authority(
        principal=principal,
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        result_reference=RESULT_REFERENCE,
        result_digest=RESULT_DIGEST,
        compatibility_receipt_reference=COMPATIBILITY_REFERENCE,
        compatibility_receipt_digest=COMPATIBILITY_DIGEST,
        analysis_weight_receipt_digest=ANALYSIS_WEIGHT_DIGEST,
        variance_design_receipt_digest=VARIANCE_DIGEST,
        verification_status="verification_pending",
        owner_contract_reference=OWNER_REFERENCE,
        owner_contract_version=7,
        owner_contract_digest=OWNER_DIGEST,
        used_at=USED_AT,
        purpose_code="selection_validity_analysis",
        policy=policy,
        read_port=read_port,
    )


def test_owner_port_cannot_append_hidden_tuple_fields_to_exact_result_record() -> None:
    """Reject exact-typed evidence with coordinates outside the canonical tuple."""
    valid = _record()
    forged = tuple.__new__(
        ValidationResultAuthorityRecord,
        (*tuple(valid), "hidden-unreviewed-owner-coordinate"),
    )

    with pytest.raises(ValidationResultAuthorityIntegrityError):
        _resolve(_ReadPort(forged))


def test_malformed_exact_result_record_maps_to_integrity_error() -> None:
    """Map a truncated exact-typed owner tuple to the domain integrity boundary."""
    valid = _record()
    forged = tuple.__new__(ValidationResultAuthorityRecord, tuple(valid)[:-1])

    with pytest.raises(ValidationResultAuthorityIntegrityError):
        _resolve(_ReadPort(forged))
