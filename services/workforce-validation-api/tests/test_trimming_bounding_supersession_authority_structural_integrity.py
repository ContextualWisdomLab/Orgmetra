"""Structural-integrity regressions for trimming/bounding supersession evidence."""

from __future__ import annotations

import pytest
from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy

from orgmetra_workforce_validation_api import ValidationPrincipal
from orgmetra_workforce_validation_api.trimming_bounding_supersession_authority import (
    TrimmingBoundingSupersessionAuthorityIntegrityError,
    TrimmingBoundingSupersessionAuthorityRecord,
    resolve_trimming_bounding_supersession_authority,
)
from test_trimming_bounding_supersession_contract import _record

READ_FIELDS = frozenset(
    {
        "adjustment_receipt_reference",
        "adjustment_receipt_digest",
        "evidence_version",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "released_at",
        "superseded_at",
        "successor_adjustment_receipt_reference",
        "successor_adjustment_receipt_digest",
        "successor_evidence_version",
        "successor_released_at",
    }
)


class _ReadPort:
    """Return configured persisted trimming supersession evidence."""

    def __init__(self, result: object) -> None:
        self.result = result

    def read_trimming_bounding_supersession_authority(self, **_: object) -> object:
        """Return configured owner evidence."""
        return self.result


def _resolve(canonical: TrimmingBoundingSupersessionAuthorityRecord, result: object) -> object:
    """Resolve the predecessor at a valid pre-cutover use instant."""
    values = dict(canonical.fields)
    return resolve_trimming_bounding_supersession_authority(
        principal=ValidationPrincipal(
            tenant_record_id=canonical.tenant_record_id,
            actor_reference="person:validation-analyst-1",
            granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
        ),
        tenant_record_id=canonical.tenant_record_id,
        validity_study_id=canonical.validity_study_id,
        adjustment_receipt_reference=values["adjustment_receipt_reference"],
        adjustment_receipt_digest=values["adjustment_receipt_digest"],
        evidence_version=values["evidence_version"],
        owner_contract_reference=values["owner_contract_reference"],
        owner_contract_version=values["owner_contract_version"],
        owner_contract_digest=values["owner_contract_digest"],
        used_at=canonical.released_at,
        purpose_code="selection_validity_analysis",
        policy=PurposeBoundAccessPolicy(
            tenant_record_id=canonical.tenant_record_id,
            policy_version_code="trimming-bounding-supersession-read-v1",
            resource_kind="trimming_bounding_supersession_authority",
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
        TrimmingBoundingSupersessionAuthorityRecord,
        tuple(canonical) + ("hidden-owner-coordinate",),
    )

    with pytest.raises(TrimmingBoundingSupersessionAuthorityIntegrityError):
        _resolve(canonical, forged)


def test_truncated_exact_typed_tuple_maps_to_integrity_error() -> None:
    canonical = _record()
    forged = tuple.__new__(
        TrimmingBoundingSupersessionAuthorityRecord,
        tuple(canonical)[:-1],
    )

    with pytest.raises(TrimmingBoundingSupersessionAuthorityIntegrityError):
        _resolve(canonical, forged)


def test_duplicate_nested_current_field_cannot_be_normalized_away() -> None:
    canonical = _record()
    raw = list(canonical)
    raw[2] = canonical.fields + (
        ("adjustment_receipt_reference", dict(canonical.fields)["adjustment_receipt_reference"]),
    )
    forged = tuple.__new__(TrimmingBoundingSupersessionAuthorityRecord, tuple(raw))

    with pytest.raises(TrimmingBoundingSupersessionAuthorityIntegrityError):
        _resolve(canonical, forged)
