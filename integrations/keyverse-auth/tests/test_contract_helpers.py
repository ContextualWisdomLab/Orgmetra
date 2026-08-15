"""Focused tests for strict OIDC configuration helper functions."""

from __future__ import annotations

import pytest

from orgmetra_keyverse_auth.contracts import _bounded_printable, _claim_name


@pytest.mark.parametrize("value", ["", " ", "x" * 6])
def test_bounded_printable_rejects_empty_or_long_values(value: str) -> None:
    with pytest.raises(ValueError, match="audience"):
        _bounded_printable(value, "audience", 5)


@pytest.mark.parametrize("value", ["api\x00value", "api\x1fvalue", "api\x7fvalue"])
def test_bounded_printable_rejects_controls(value: str) -> None:
    with pytest.raises(ValueError, match="control"):
        _bounded_printable(value, "audience", 20)


def test_bounded_printable_normalizes_valid_value() -> None:
    assert _bounded_printable("  orgmetra-api  ", "audience", 20) == "orgmetra-api"


@pytest.mark.parametrize(
    "value",
    ["", " ", "x" * 65, "UPPER", "claim-name", "café"],
)
def test_claim_name_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError, match="claim_name"):
        _claim_name(value, "claim_name")


def test_claim_name_normalizes_valid_ascii_value() -> None:
    assert _claim_name(" tenant_claim ", "claim_name") == "tenant_claim"
