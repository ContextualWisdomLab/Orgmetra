"""Fail closed when released weight-eligibility evidence has a successor."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from inspect import signature
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
RECEIPT_REFERENCE = "weight_eligibility_receipt:11111111-1111-4111-8111-111111111111"
SUCCESSOR_REFERENCE = "weight_eligibility_receipt:33333333-3333-4333-8333-333333333333"
OWNER_CONTRACT_REFERENCE = "released_owner_contract:22222222-2222-4222-8222-222222222222"
RECEIPT_DIGEST = "1" * 64
SUCCESSOR_DIGEST = "3" * 64
OWNER_CONTRACT_DIGEST = "2" * 64
OWNER_CONTRACT_RELEASED_AT = datetime(2026, 7, 1, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 7, 15, tzinfo=timezone.utc)
CUTOVER_AT = datetime(2026, 9, 17, tzinfo=timezone.utc)
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
    """Return one configured correction state through the owner read shape."""

    def __init__(self, record: WeightEligibilitySupersessionAuthorityRecord) -> None:
        self.record = record

    def read_weight_eligibility_supersession_authority(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        eligibility_receipt_reference: str,
        eligibility_receipt_digest: str,
        evidence_version: int,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
    ) -> WeightEligibilitySupersessionAuthorityRecord:
        """Return owner evidence; the resolver verifies every current coordinate."""
        del (
            tenant_record_id,
            validity_study_id,
            eligibility_receipt_reference,
            eligibility_receipt_digest,
            evidence_version,
            owner_contract_reference,
            owner_contract_version,
            owner_contract_digest,
        )
        return self.record


def _principal() -> ValidationPrincipal:
    """Return one exact workforce-validation principal."""
    return ValidationPrincipal(
        tenant_record_id=TENANT,
        actor_reference="person:validation-analyst-1",
        granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
    )


def _policy() -> PurposeBoundAccessPolicy:
    """Authorize the full internal correction evidence while minimizing the view."""
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="weight-eligibility-supersession-read-v1",
        resource_kind="weight_eligibility_supersession_authority",
        purpose_code="selection_validity_analysis",
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=READ_FIELDS,
    )


def _record(
    *,
    superseded_at: datetime | None = CUTOVER_AT,
    successor_reference: str | None = SUCCESSOR_REFERENCE,
    successor_digest: str | None = SUCCESSOR_DIGEST,
    successor_evidence_version: int | None = 1,
    successor_released_at: datetime | None = CUTOVER_AT,
    owner_contract_released_at: datetime = OWNER_CONTRACT_RELEASED_AT,
) -> WeightEligibilitySupersessionAuthorityRecord:
    """Build one canonical current or superseded eligibility authority record."""
    return WeightEligibilitySupersessionAuthorityRecord(
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        eligibility_receipt_reference=RECEIPT_REFERENCE,
        eligibility_receipt_digest=RECEIPT_DIGEST,
        evidence_version=1,
        owner_contract_reference=OWNER_CONTRACT_REFERENCE,
        owner_contract_version=3,
        owner_contract_digest=OWNER_CONTRACT_DIGEST,
        owner_contract_released_at=owner_contract_released_at,
        released_at=RELEASED_AT,
        superseded_at=superseded_at,
        successor_eligibility_receipt_reference=successor_reference,
        successor_eligibility_receipt_digest=successor_digest,
        successor_evidence_version=successor_evidence_version,
        successor_released_at=successor_released_at,
    )


def _resolve(
    record: WeightEligibilitySupersessionAuthorityRecord,
    *,
    used_at: datetime,
):
    """Resolve one historical eligibility authority instant."""
    return resolve_weight_eligibility_supersession_authority(
        principal=_principal(),
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        eligibility_receipt_reference=RECEIPT_REFERENCE,
        eligibility_receipt_digest=RECEIPT_DIGEST,
        evidence_version=1,
        owner_contract_reference=OWNER_CONTRACT_REFERENCE,
        owner_contract_version=3,
        owner_contract_digest=OWNER_CONTRACT_DIGEST,
        used_at=used_at,
        purpose_code="selection_validity_analysis",
        policy=_policy(),
        read_port=_ReadPort(record),
    )


def test_successor_chronology_is_owner_evidence_not_caller_input() -> None:
    """Keep cutover and successor coordinates out of caller-controlled resolution."""
    parameters = signature(resolve_weight_eligibility_supersession_authority).parameters
    assert "owner_contract_released_at" not in parameters
    assert "released_at" not in parameters
    assert "superseded_at" not in parameters
    assert "successor_eligibility_receipt_reference" not in parameters
    assert "successor_eligibility_receipt_digest" not in parameters
    assert "successor_evidence_version" not in parameters
    assert "successor_released_at" not in parameters


def test_historical_use_before_cutover_remains_verifiable_without_successor_disclosure() -> None:
    """Allow predecessor reconstruction before cutover without leaking successor evidence."""
    view = _resolve(_record(), used_at=CUTOVER_AT - timedelta(microseconds=1))
    fields = dict(view.fields)
    assert fields["eligibility_receipt_reference"] == RECEIPT_REFERENCE
    assert fields["eligibility_receipt_digest"] == RECEIPT_DIGEST
    assert fields["released_at"] == RELEASED_AT
    assert "superseded_at" not in fields
    assert "successor_eligibility_receipt_reference" not in fields
    assert "successor_released_at" not in fields


def test_use_at_or_after_cutover_fails_closed() -> None:
    """Reject stale eligibility evidence at the exact successor cutover and later."""
    record = _record()
    for used_at in (CUTOVER_AT, CUTOVER_AT + timedelta(seconds=1)):
        with pytest.raises(WeightEligibilitySupersessionAuthorityIntegrityError):
            _resolve(record, used_at=used_at)


def test_owner_contract_cannot_retroactively_authorize_receipt() -> None:
    """Require the governing contract to exist before eligibility release."""
    with pytest.raises(ValueError, match="owner contract"):
        _record(owner_contract_released_at=RELEASED_AT + timedelta(microseconds=1))


def test_unsuperseded_receipt_remains_current() -> None:
    """Keep a released receipt current when no complete successor edge exists."""
    record = _record(
        superseded_at=None,
        successor_reference=None,
        successor_digest=None,
        successor_evidence_version=None,
        successor_released_at=None,
    )
    _resolve(record, used_at=CUTOVER_AT + timedelta(days=30))


@pytest.mark.parametrize(
    (
        "superseded_at",
        "successor_reference",
        "successor_digest",
        "successor_evidence_version",
        "successor_released_at",
    ),
    [
        (CUTOVER_AT, None, SUCCESSOR_DIGEST, 1, CUTOVER_AT),
        (None, SUCCESSOR_REFERENCE, SUCCESSOR_DIGEST, 1, CUTOVER_AT),
        (CUTOVER_AT, RECEIPT_REFERENCE, SUCCESSOR_DIGEST, 1, CUTOVER_AT),
        (CUTOVER_AT, SUCCESSOR_REFERENCE, RECEIPT_DIGEST, 1, CUTOVER_AT),
        (CUTOVER_AT, SUCCESSOR_REFERENCE, SUCCESSOR_DIGEST, 2, CUTOVER_AT),
        (
            RELEASED_AT,
            SUCCESSOR_REFERENCE,
            SUCCESSOR_DIGEST,
            1,
            RELEASED_AT,
        ),
        (
            CUTOVER_AT,
            SUCCESSOR_REFERENCE,
            SUCCESSOR_DIGEST,
            1,
            CUTOVER_AT - timedelta(microseconds=1),
        ),
        (
            CUTOVER_AT,
            SUCCESSOR_REFERENCE,
            SUCCESSOR_DIGEST,
            1,
            CUTOVER_AT + timedelta(microseconds=1),
        ),
    ],
)
def test_supersession_requires_one_complete_atomic_successor_edge(
    superseded_at: datetime | None,
    successor_reference: str | None,
    successor_digest: str | None,
    successor_evidence_version: int | None,
    successor_released_at: datetime | None,
) -> None:
    """Reject partial, self-referential, schema-floating, or non-atomic successor evidence."""
    with pytest.raises(ValueError):
        _record(
            superseded_at=superseded_at,
            successor_reference=successor_reference,
            successor_digest=successor_digest,
            successor_evidence_version=successor_evidence_version,
            successor_released_at=successor_released_at,
        )
