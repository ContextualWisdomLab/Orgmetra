"""Structural-integrity regressions for nonresponse-adjustment owner evidence."""

from __future__ import annotations

import pytest

from orgmetra_workforce_validation_api.nonresponse_adjustment_authority import (
    NonresponseAdjustmentAuthorityIntegrityError,
    NonresponseAdjustmentAuthorityRecord,
)
from test_nonresponse_adjustment_authority import _ReadPort, _record, _resolve


def test_hidden_trailing_tuple_structure_fails_closed() -> None:
    canonical = _record()
    forged = tuple.__new__(
        NonresponseAdjustmentAuthorityRecord,
        tuple(canonical) + ("hidden-owner-coordinate",),
    )

    with pytest.raises(NonresponseAdjustmentAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(forged))


def test_truncated_exact_typed_tuple_maps_to_integrity_error() -> None:
    canonical = _record()
    forged = tuple.__new__(
        NonresponseAdjustmentAuthorityRecord,
        tuple(canonical)[:-1],
    )

    with pytest.raises(NonresponseAdjustmentAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(forged))
