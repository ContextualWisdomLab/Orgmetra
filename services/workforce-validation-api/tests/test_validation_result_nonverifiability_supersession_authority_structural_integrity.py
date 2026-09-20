"""Reject non-canonical exact-typed v1 non-verifiability supersession evidence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.result_nonverifiability_supersession_authority import (
    ValidationResultNonVerifiabilitySupersessionAuthorityIntegrityError,
    ValidationResultNonVerifiabilitySupersessionAuthorityRecord,
    resolve_validation_result_nonverifiability_supersession_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
RESULT_REFERENCE = "validation_analysis_result:11111111-1111-4111-8111-111111111111"
OWNER_CONTRACT_REFERENCE = "released_owner_contract:22222222-2222-4222-8222-222222222222"
ATTEMPT_REFERENCE = "validation_evidence_verification_attempt:33333333-3333-4333-8333-333333333333"
SUCCESSOR_ATTEMPT_REFERENCE = "validation_evidence_verification_attempt:44444444-4444-4444-8444-444444444444"
RESULT_DIGEST = "1" * 64
OWNER_CONTRACT_DIGEST = "2" * 64
ATTEMPT_DIGEST = "3" * 64
SUCCESSOR_ATTEMPT_DIGEST = "4" * 64
OWNER_CONTRACT_RELEASED_AT = datetime(2026, 9, 1, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 18, 8, tzinfo=timezone.utc)
USED_AT = datetime(2026, 9, 18, 10, tzinfo=timezone.utc)
CUTOVER = USED_AT + timedelta(hours=1)
READ_FIELDS = frozenset(
    {
        "result_reference",
        "result_digest",
        "failed_evidence_kind",
        "failure_mode",
        "verification_attempt_reference",
        "verification_attempt_digest",
        "evidence_version",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "released_at",
        "superseded_at",
        "successor_target_result_reference",
        "successor_target_result_digest",
        "successor_failed_evidence_kind",
        "successor_verification_attempt_reference",
        "successor_verification_attempt_digest",
        "successor_verification_attempt_released_at",
    }
)


class _ReadPort:
    """Return one configured object so resolver integrity owns the trust decision."""

    def __init__(self, record: object) -> None:
        self.record = record

    def read_validation_result_nonverifiability_supersession_authority(
        self, **_: object
    ) -> object:
        """Return the configured owner evidence without normalizing its structure."""
        return self.record


def _record() -> ValidationResultNonVerifiabilitySupersessionAuthorityRecord:
    """Build one canonical predecessor with a later same-obligation successor."""
    return ValidationResultNonVerifiabilitySupersessionAuthorityRecord(
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        result_reference=RESULT_REFERENCE,
        result_digest=RESULT_DIGEST,
        failed_evidence_kind="analysis_weight_receipt",
        failure_mode="missing",
        verification_attempt_reference=ATTEMPT_REFERENCE,
        verification_attempt_digest=ATTEMPT_DIGEST,
        evidence_version=1,
        owner_contract_reference=OWNER_CONTRACT_REFERENCE,
        owner_contract_version=3,
        owner_contract_digest=OWNER_CONTRACT_DIGEST,
        owner_contract_released_at=OWNER_CONTRACT_RELEASED_AT,
        released_at=RELEASED_AT,
        superseded_at=CUTOVER,
        successor_target_result_reference=RESULT_REFERENCE,
        successor_target_result_digest=RESULT_DIGEST,
        successor_failed_evidence_kind="analysis_weight_receipt",
        successor_verification_attempt_reference=SUCCESSOR_ATTEMPT_REFERENCE,
        successor_verification_attempt_digest=SUCCESSOR_ATTEMPT_DIGEST,
        successor_verification_attempt_released_at=CUTOVER,
    )


def _resolve(record: object) -> None:
    """Resolve through the public owner boundary at a historical use instant."""
    resolve_validation_result_nonverifiability_supersession_authority(
        principal=ValidationPrincipal(
            tenant_record_id=TENANT,
            actor_reference="person:validation-analyst-1",
            granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
        ),
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        result_reference=RESULT_REFERENCE,
        result_digest=RESULT_DIGEST,
        failed_evidence_kind="analysis_weight_receipt",
        failure_mode="missing",
        verification_attempt_reference=ATTEMPT_REFERENCE,
        verification_attempt_digest=ATTEMPT_DIGEST,
        evidence_version=1,
        owner_contract_reference=OWNER_CONTRACT_REFERENCE,
        owner_contract_version=3,
        owner_contract_digest=OWNER_CONTRACT_DIGEST,
        used_at=USED_AT,
        purpose_code="selection_validity_analysis",
        policy=PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="validation-result-nonverifiability-supersession-read-v1",
            resource_kind="validation_result_nonverifiability_supersession_authority",
            purpose_code="selection_validity_analysis",
            operation_code="read",
            required_scope_code="orgmetra.workforce_validation.read",
            permitted_fields=READ_FIELDS,
        ),
        read_port=_ReadPort(record),
    )


def test_v1_supersession_rejects_hidden_outer_tuple_member() -> None:
    """Do not normalize away an exact-typed hidden coordinate after owner read."""
    canonical = _record()
    forged = tuple.__new__(
        ValidationResultNonVerifiabilitySupersessionAuthorityRecord,
        tuple(canonical) + ("hidden-owner-coordinate",),
    )

    with pytest.raises(ValidationResultNonVerifiabilitySupersessionAuthorityIntegrityError):
        _resolve(forged)


def test_v1_supersession_maps_truncated_tuple_to_integrity_error() -> None:
    """Keep malformed exact-typed evidence inside the family integrity boundary."""
    canonical = _record()
    forged = tuple.__new__(
        ValidationResultNonVerifiabilitySupersessionAuthorityRecord,
        tuple(canonical)[:5],
    )

    with pytest.raises(ValidationResultNonVerifiabilitySupersessionAuthorityIntegrityError):
        _resolve(forged)


def test_v1_supersession_rejects_duplicate_nested_current_field() -> None:
    """Reject duplicate nested coordinates that dict conversion would erase."""
    canonical = _record()
    forged_items = list(canonical)
    forged_items[2] = canonical.fields + (("result_reference", RESULT_REFERENCE),)
    forged = tuple.__new__(
        ValidationResultNonVerifiabilitySupersessionAuthorityRecord,
        tuple(forged_items),
    )

    with pytest.raises(ValidationResultNonVerifiabilitySupersessionAuthorityIntegrityError):
        _resolve(forged)
