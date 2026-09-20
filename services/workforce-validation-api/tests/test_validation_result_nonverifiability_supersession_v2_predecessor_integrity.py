"""Require v2 correction authority to revalidate the complete predecessor contract."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api.registry import ValidationPrincipal
from orgmetra_workforce_validation_api.result_nonverifiability import (
    ValidationResultNonVerifiabilityRecord,
)
from orgmetra_workforce_validation_api.result_nonverifiability_supersession_v2_authority import (
    ValidationResultNonVerifiabilitySupersessionV2AuthorityIntegrityError,
    ValidationResultNonVerifiabilitySupersessionV2AuthorityRecord,
    _READ_FIELDS,
    resolve_validation_result_nonverifiability_supersession_v2_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
RESULT_REFERENCE = "validation_analysis_result:11111111-1111-4111-8111-111111111111"
FAILED_REFERENCE = "analysis_weight_receipt:22222222-2222-4222-8222-222222222222"
ATTEMPT_REFERENCE = "validation_evidence_verification_attempt:33333333-3333-4333-8333-333333333333"
OWNER_REFERENCE = "released_owner_contract:55555555-5555-4555-8555-555555555555"
RESULT_DIGEST = "1" * 64
FAILED_DIGEST = "2" * 64
ATTEMPT_DIGEST = "3" * 64
OWNER_DIGEST = "5" * 64
OWNER_RELEASED_AT = datetime(2026, 9, 17, 5, 55, tzinfo=timezone.utc)
FAILED_RELEASED_AT = datetime(2026, 9, 17, 5, 59, tzinfo=timezone.utc)
EVALUATED_AT = datetime(2026, 9, 17, 6, 0, tzinfo=timezone.utc)
ATTEMPT_RELEASED_AT = datetime(2026, 9, 17, 6, 2, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 17, 6, 5, tzinfo=timezone.utc)
USED_AT = datetime(2026, 9, 17, 6, 10, tzinfo=timezone.utc)


def _predecessor() -> ValidationResultNonVerifiabilityRecord:
    """Build one canonical non-reproducible predecessor before structural corruption."""
    return ValidationResultNonVerifiabilityRecord(
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        result_reference=RESULT_REFERENCE,
        result_digest=RESULT_DIGEST,
        failed_evidence_kind="analysis_weight_receipt",
        failure_mode="non_reproducible",
        failed_evidence_reference=FAILED_REFERENCE,
        failed_evidence_digest=FAILED_DIGEST,
        failed_evidence_released_at=FAILED_RELEASED_AT,
        verification_attempt_reference=ATTEMPT_REFERENCE,
        verification_attempt_digest=ATTEMPT_DIGEST,
        verification_attempt_released_at=ATTEMPT_RELEASED_AT,
        owner_contract_reference=OWNER_REFERENCE,
        owner_contract_version=7,
        owner_contract_digest=OWNER_DIGEST,
        owner_contract_released_at=OWNER_RELEASED_AT,
        evaluated_at=EVALUATED_AT,
        released_at=RELEASED_AT,
    )


class _ReadPort:
    """Return configured owner evidence through the v2 read capability."""

    def __init__(self, result: object) -> None:
        self.result = result

    def read_validation_result_nonverifiability_supersession_v2_authority(
        self, **coordinates: object
    ) -> object:
        """Return configured evidence after accepting caller-known lookup coordinates."""
        del coordinates
        return self.result


def _policy() -> PurposeBoundAccessPolicy:
    """Permit the full owner evidence set used by the v2 resolver."""
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="validation-result-nonverifiability-supersession-read-v2",
        resource_kind="validation_result_nonverifiability_supersession_authority",
        purpose_code="selection_validity_analysis",
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=_READ_FIELDS,
    )


def _principal() -> ValidationPrincipal:
    """Return one tenant-bound validation reader."""
    return ValidationPrincipal(
        tenant_record_id=TENANT,
        actor_reference="person:validation-analyst-1",
        granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
    )


@pytest.mark.parametrize(
    ("tuple_index", "hostile_value"),
    [
        (7, RESULT_DIGEST),
        (13, EVALUATED_AT + timedelta(seconds=1)),
        (17, EVALUATED_AT + timedelta(seconds=1)),
        (18, EVALUATED_AT - timedelta(seconds=1)),
    ],
)
def test_v2_revalidates_full_predecessor_invariants(
    tuple_index: int, hostile_value: object
) -> None:
    """Reject exact-typed predecessors forged around v1 digest or chronology guards."""
    canonical = _predecessor()
    forged_values = list(canonical)
    forged_values[tuple_index] = hostile_value
    forged = tuple.__new__(ValidationResultNonVerifiabilityRecord, forged_values)

    with pytest.raises(ValueError):
        ValidationResultNonVerifiabilitySupersessionV2AuthorityRecord(
            predecessor=forged,
            evidence_version=2,
        )


def test_resolver_revalidates_exact_typed_owner_evidence() -> None:
    """Reject a structurally forged v2 record returned directly by an owner adapter."""
    canonical_predecessor = _predecessor()
    forged_values = list(canonical_predecessor)
    forged_values[13] = EVALUATED_AT + timedelta(seconds=1)
    forged_predecessor = tuple.__new__(
        ValidationResultNonVerifiabilityRecord, forged_values
    )
    canonical_authority = ValidationResultNonVerifiabilitySupersessionV2AuthorityRecord(
        predecessor=canonical_predecessor,
        evidence_version=2,
    )
    forged_authority = tuple.__new__(
        ValidationResultNonVerifiabilitySupersessionV2AuthorityRecord,
        (
            forged_predecessor,
            canonical_authority.evidence_version,
            canonical_authority.superseded_at,
            canonical_authority.successor_fields,
        ),
    )

    with pytest.raises(ValidationResultNonVerifiabilitySupersessionV2AuthorityIntegrityError):
        resolve_validation_result_nonverifiability_supersession_v2_authority(
            principal=_principal(),
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            result_reference=RESULT_REFERENCE,
            result_digest=RESULT_DIGEST,
            failed_evidence_kind="analysis_weight_receipt",
            failed_evidence_reference=FAILED_REFERENCE,
            failed_evidence_digest=FAILED_DIGEST,
            verification_attempt_reference=ATTEMPT_REFERENCE,
            verification_attempt_digest=ATTEMPT_DIGEST,
            evidence_version=2,
            owner_contract_reference=OWNER_REFERENCE,
            owner_contract_version=7,
            owner_contract_digest=OWNER_DIGEST,
            used_at=USED_AT,
            purpose_code="selection_validity_analysis",
            policy=_policy(),
            read_port=_ReadPort(forged_authority),
        )
