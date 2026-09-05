"""Reject non-canonical allocation-ratio text before Decimal parsing."""

from __future__ import annotations

import pytest

from orgmetra_people_api.mutations import parse_allocation_ratio


class _AllocationRatioText(str):
    """Represent a valid-looking allocation token with caller-defined runtime identity."""


def test_parse_allocation_ratio_rejects_string_subclasses() -> None:
    """Assignment allocation text must be the exact built-in value that was parsed."""
    with pytest.raises(ValueError, match="allocation_ratio"):
        parse_allocation_ratio(_AllocationRatioText("0.2500"))
