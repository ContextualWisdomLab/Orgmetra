"""Regression coverage for canonical validation-result supersession owner structure."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.result_supersession_authority import (
    ValidationResultSupersessionAuthorityIntegrityError,
    ValidationResultSupersessionAuthorityRecord,
    resolve_validation_result_supersession_authority,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000d1")
RESULT_REFERENCE = "validation_analysis_result:11111111-1111-4111-8111-111111111111"
OWNER_REFERENCE = "released_owner_contract:22222222-2222-4222-8222-222222222222"
RESULT_DIGEST = "1" * 64
OWNER_DIGEST = "2" * 64
OWNER_RELEASED_AT = datetime(2026, 9, 1, tzinfo=timezone.utc)
RELEASED_AT = datetime(2026, 9, 17, 10, tzinfo=timezone.utc)
USED_AT = datetime(2026, 9, 17, 12, tzinfo=timezone.utc)
READ_FIELDS = frozenset(
    {
        "result_reference",
        "result_digest",
        "evidence_version",
        "correction_sequence",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "released_at",
        "superseded_at",
        "successor_result_reference",
        "successor_correction_sequence",
        "successor_result_digest",
        "successor_released_at",
    }
)


class _ReadPort:
    """Return configured owner evidence without normalizing tuple structure."""

    def __init__(self, result: object) -> None:
        self.result = result

    def read_validation_result_supersession_authority(self, **_: object) -> object:
        """Return the configured raw owner result."""
        return self.result


def _record() -> ValidationResultSupersessionAuthorityRecord:
    """Build one current canonical validation-result supersession record."""
    return ValidationResultSupersessionAuthorityRecord(
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        result_reference=RESULT_REFERENCE,
        result_digest=RESULT_DIGEST,
        evidence_version=1,
        correction_sequence=2,
        owner_contract_reference=OWNER_REFERENCE,
        owner_contract_version=3,
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
        policy_version_code="validation-result-supersession-authority-read-v1",
        resource_kind="validation_result_supersession_authority",
        purpose_code="selection_validity_analysis",
        operation_code="read",
        required_scope_code="orgmetra.workforce_validation.read",
        permitted_fields=READ_FIELDS,
    )
    return resolve_validation_result_supersession_authority(
        principal=principal,
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        result_reference=RESULT_REFERENCE,
        result_digest=RESULT_DIGEST,
        evidence_version=1,
        correction_sequence=2,
        owner_contract_reference=OWNER_REFERENCE,
        owner_contract_version=3,
        owner_contract_digest=OWNER_DIGEST,
        used_at=USED_AT,
        purpose_code="selection_validity_analysis",
        policy=policy,
        read_port=read_port,
    )


def test_owner_port_cannot_append_hidden_tuple_fields_to_exact_result_supersession_record() -> None:
    """Reject exact-typed evidence with coordinates outside the canonical tuple."""
    valid = _record()
    forged = tuple.__new__(
        ValidationResultSupersessionAuthorityRecord,
        (*tuple(valid), "hidden-unreviewed-owner-coordinate"),
    )

    with pytest.raises(ValidationResultSupersessionAuthorityIntegrityError):
        _resolve(_ReadPort(forged))


def test_malformed_exact_result_supersession_record_maps_to_integrity_error() -> None:
    """Map truncated exact-typed evidence to the domain integrity boundary."""
    valid = _record()
    forged = tuple.__new__(ValidationResultSupersessionAuthorityRecord, tuple(valid)[:-1])

    with pytest.raises(ValidationResultSupersessionAuthorityIntegrityError):
        _resolve(_ReadPort(forged))
