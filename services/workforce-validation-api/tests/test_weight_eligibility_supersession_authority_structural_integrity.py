"""Structural-integrity regressions for weight-eligibility supersession evidence."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest
from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy

from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.weight_eligibility_supersession_authority import (
    WeightEligibilitySupersessionAuthorityIntegrityError,
    WeightEligibilitySupersessionAuthorityRecord,
    resolve_weight_eligibility_supersession_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
RECEIPT = "weight_eligibility_receipt:11111111-1111-4111-8111-111111111111"
SUCCESSOR = "weight_eligibility_receipt:22222222-2222-4222-8222-222222222222"
OWNER = "released_owner_contract:33333333-3333-4333-8333-333333333333"
RECEIPT_DIGEST = "1" * 64
SUCCESSOR_DIGEST = "2" * 64
OWNER_DIGEST = "3" * 64
OWNER_RELEASED_AT = datetime(2026, 9, 17, 0, 30, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 17, 1, 0, tzinfo=timezone.utc)
CUTOVER = datetime(2026, 9, 18, 1, 0, tzinfo=timezone.utc)
READ_FIELDS = frozenset(
    {
        "eligibility_receipt_reference",
        "eligibility_receipt_digest",
        "evidence_version",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "released_at",
        "superseded_at",
        "successor_eligibility_receipt_reference",
        "successor_eligibility_receipt_digest",
        "successor_evidence_version",
        "successor_released_at",
    }
)


class _ReadPort:
    """Return configured persisted supersession evidence."""

    def __init__(self, result: object) -> None:
        self.result = result

    def read_weight_eligibility_supersession_authority(self, **_: object) -> object:
        """Return the configured owner evidence."""
        return self.result


def _record() -> WeightEligibilitySupersessionAuthorityRecord:
    """Build one canonical eligibility correction edge."""
    return WeightEligibilitySupersessionAuthorityRecord(
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        eligibility_receipt_reference=RECEIPT,
        eligibility_receipt_digest=RECEIPT_DIGEST,
        evidence_version=1,
        owner_contract_reference=OWNER,
        owner_contract_version=1,
        owner_contract_digest=OWNER_DIGEST,
        owner_contract_released_at=OWNER_RELEASED_AT,
        released_at=RELEASED_AT,
        superseded_at=CUTOVER,
        successor_eligibility_receipt_reference=SUCCESSOR,
        successor_eligibility_receipt_digest=SUCCESSOR_DIGEST,
        successor_evidence_version=1,
        successor_released_at=CUTOVER,
    )


def _resolve(result: object) -> object:
    """Resolve the predecessor at a valid pre-cutover use instant."""
    return resolve_weight_eligibility_supersession_authority(
        principal=ValidationPrincipal(
            tenant_record_id=TENANT,
            actor_reference="person:validation-analyst-1",
            granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
        ),
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        eligibility_receipt_reference=RECEIPT,
        eligibility_receipt_digest=RECEIPT_DIGEST,
        evidence_version=1,
        owner_contract_reference=OWNER,
        owner_contract_version=1,
        owner_contract_digest=OWNER_DIGEST,
        used_at=RELEASED_AT,
        purpose_code="selection_validity_analysis",
        policy=PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="weight-eligibility-supersession-read-v1",
            resource_kind="weight_eligibility_supersession_authority",
            purpose_code="selection_validity_analysis",
            operation_code="read",
            required_scope_code="orgmetra.workforce_validation.read",
            permitted_fields=READ_FIELDS,
        ),
        read_port=_ReadPort(result),
    )


def test_hidden_trailing_tuple_structure_fails_closed() -> None:
    canonical = _record()
    forged = tuple.__new__(
        WeightEligibilitySupersessionAuthorityRecord,
        tuple(canonical) + ("hidden-owner-coordinate",),
    )

    with pytest.raises(WeightEligibilitySupersessionAuthorityIntegrityError):
        _resolve(forged)


def test_truncated_exact_typed_tuple_maps_to_integrity_error() -> None:
    canonical = _record()
    forged = tuple.__new__(
        WeightEligibilitySupersessionAuthorityRecord,
        tuple(canonical)[:-1],
    )

    with pytest.raises(WeightEligibilitySupersessionAuthorityIntegrityError):
        _resolve(forged)


def test_duplicate_nested_current_field_cannot_be_normalized_away() -> None:
    canonical = _record()
    raw = list(canonical)
    raw[2] = canonical.fields + (("eligibility_receipt_reference", RECEIPT),)
    forged = tuple.__new__(WeightEligibilitySupersessionAuthorityRecord, tuple(raw))

    with pytest.raises(WeightEligibilitySupersessionAuthorityIntegrityError):
        _resolve(forged)
