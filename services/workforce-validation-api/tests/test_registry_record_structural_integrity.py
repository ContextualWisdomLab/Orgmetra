"""Structural-integrity regressions for persisted validity-study records."""

from __future__ import annotations

import pytest

from orgmetra_workforce_validation_api.registry import (
    ValidityStudyIntegrityError,
    ValidityStudyRecord,
    read_validity_study,
)
from test_registry import STUDY, TENANT, _ReadPort, _policy, _principal, _record


def _resolve(result: object) -> object:
    """Resolve one requested field through the canonical registry boundary."""
    return read_validity_study(
        principal=_principal(),
        tenant_record_id=TENANT,
        validity_study_id=STUDY,
        purpose_code="validation_review",
        requested_fields=frozenset({"study_status_code"}),
        policy=_policy(),
        read_port=_ReadPort(result),
    )


def test_hidden_trailing_tuple_structure_fails_closed() -> None:
    canonical = _record()
    forged = tuple.__new__(
        ValidityStudyRecord,
        tuple(canonical) + ("hidden-persistence-coordinate",),
    )

    with pytest.raises(ValidityStudyIntegrityError):
        _resolve(forged)


def test_truncated_exact_typed_tuple_maps_to_integrity_error() -> None:
    canonical = _record()
    forged = tuple.__new__(ValidityStudyRecord, tuple(canonical)[:-1])

    with pytest.raises(ValidityStudyIntegrityError):
        _resolve(forged)
