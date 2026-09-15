"""Reject non-canonical allocation-ratio text before Decimal parsing."""

from __future__ import annotations

from pathlib import Path
import re

import pytest

from orgmetra_people_api.mutations import parse_allocation_ratio

_OPENAPI_PATH = Path(__file__).resolve().parents[3] / "schemas" / "openapi.yaml"


class _AllocationRatioText(str):
    """Represent a valid-looking allocation token with caller-defined runtime identity."""


def _published_allocation_pattern() -> re.Pattern[str]:
    """Read the Assignment allocation token pattern from the published OpenAPI contract."""
    schema = _OPENAPI_PATH.read_text(encoding="utf-8")
    match = re.search(
        r"allocation_ratio:\n\s+type: string\n\s+pattern: '([^']+)'",
        schema,
    )
    assert match is not None, "CreateAssignmentRecordCommand allocation pattern is missing"
    return re.compile(match.group(1))


def test_parse_allocation_ratio_rejects_string_subclasses() -> None:
    """Assignment allocation text must be the exact built-in value that was parsed."""
    with pytest.raises(ValueError, match="allocation_ratio"):
        parse_allocation_ratio(_AllocationRatioText("0.2500"))


def test_parse_allocation_ratio_rejects_zero_before_domain_construction() -> None:
    """The HTTP scalar parser must enforce the same strictly-positive Assignment invariant."""
    with pytest.raises(ValueError, match="allocation_ratio"):
        parse_allocation_ratio("0.0000")


def test_openapi_allocation_pattern_matches_the_strictly_positive_domain_range() -> None:
    """Generated clients and handlers must not advertise zero as a valid Assignment ratio."""
    pattern = _published_allocation_pattern()
    assert pattern.fullmatch("0.0000") is None
    for token in ("0.0001", "0.2500", "0.9999", "1.0000"):
        assert pattern.fullmatch(token) is not None
