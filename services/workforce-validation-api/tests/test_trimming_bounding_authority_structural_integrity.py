"""Structural-integrity regressions for trimming/bounding owner evidence."""

from __future__ import annotations

import pytest

from orgmetra_workforce_validation_api.trimming_bounding_authority import (
    TrimmingBoundingAuthorityIntegrityError,
    TrimmingBoundingAuthorityRecord,
)
from test_trimming_bounding_authority import _ReadPort, _record, _resolve


def test_hidden_trailing_tuple_structure_fails_closed() -> None:
    canonical = _record()
    forged = tuple.__new__(
        TrimmingBoundingAuthorityRecord,
        tuple(canonical) + ("hidden-owner-coordinate",),
    )

    with pytest.raises(TrimmingBoundingAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(forged))


def test_truncated_exact_typed_tuple_maps_to_integrity_error() -> None:
    canonical = _record()
    forged = tuple.__new__(
        TrimmingBoundingAuthorityRecord,
        tuple(canonical)[:-1],
    )

    with pytest.raises(TrimmingBoundingAuthorityIntegrityError):
        _resolve(read_port=_ReadPort(forged))
