"""Focused branch coverage for strict JOSE and claim helper functions."""

from __future__ import annotations

import math
from collections.abc import Mapping

import pytest

import orgmetra_keyverse_auth.authorizer as authorizer_module
from orgmetra_keyverse_auth.authorizer import (
    _claim_string,
    _decode_claims,
    _header_value,
    _numeric_date,
    _purpose_code,
    _purpose_collection,
    _scope_code,
    _scope_collection,
    _unverified_header,
)
from orgmetra_people_api import AuthenticationFailed


class _MappingOnly(Mapping[str, object]):
    """Provide a mapping implementation distinct from a built-in dictionary."""

    def __init__(self, values: dict[str, object]) -> None:
        self._values = values

    def __getitem__(self, key: str) -> object:
        return self._values[key]

    def __iter__(self):
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)


def test_unverified_header_rejects_non_mapping_result(monkeypatch) -> None:
    monkeypatch.setattr(authorizer_module.jwt, "get_unverified_header", lambda _token: [])

    with pytest.raises(AuthenticationFailed, match="header is invalid"):
        _unverified_header("a.b.c")


def test_header_value_accepts_mapping_and_rejects_invalid_shapes() -> None:
    assert _header_value(_MappingOnly({"kid": " key-1 "}), "kid", 10) == "key-1"

    for header in (
        {"kid": None},
        {"kid": ""},
        {"kid": "x" * 11},
        {"kid": "key\x7f"},
        {"kid": "kéy"},
    ):
        with pytest.raises(AuthenticationFailed, match="kid"):
            _header_value(header, "kid", 10)


def test_decode_claims_rejects_non_mapping_result(monkeypatch, oidc_config) -> None:
    monkeypatch.setattr(authorizer_module.jwt, "decode", lambda *_args, **_kwargs: [])

    class _SigningKey:
        key = object()

    with pytest.raises(AuthenticationFailed, match="claims are invalid"):
        _decode_claims(
            "a.b.c",
            _SigningKey(),  # type: ignore[arg-type]
            algorithm="RS256",
            config=oidc_config,
        )


@pytest.mark.parametrize(
    "value",
    [None, 1, "", "x" * 6, "abc\x1f"],
)
def test_claim_string_rejects_non_string_empty_long_and_control(value: object) -> None:
    with pytest.raises(AuthenticationFailed, match="subject claim is invalid"):
        _claim_string({"subject": value}, "subject", 5)


def test_claim_string_normalizes_printable_value() -> None:
    assert _claim_string({"subject": "  actor-1  "}, "subject", 20) == "actor-1"


@pytest.mark.parametrize("value", [True, False, None, "123", object()])
def test_numeric_date_rejects_boolean_or_non_numeric(value: object) -> None:
    with pytest.raises(AuthenticationFailed, match="iat claim is invalid"):
        _numeric_date({"iat": value}, "iat")


@pytest.mark.parametrize("value", [math.inf, -math.inf, math.nan])
def test_numeric_date_rejects_non_finite_value(value: float) -> None:
    with pytest.raises(AuthenticationFailed, match="exp claim is invalid"):
        _numeric_date({"exp": value}, "exp")


def test_numeric_date_accepts_int_and_float() -> None:
    assert _numeric_date({"iat": 1}, "iat") == 1.0
    assert _numeric_date({"iat": 1.5}, "iat") == 1.5


@pytest.mark.parametrize(
    "value",
    [None, "people_read", b"people_read", [], ["purpose"] * 65],
)
def test_purpose_collection_rejects_invalid_collection_shape(value: object) -> None:
    with pytest.raises(AuthenticationFailed, match="purposes claim is invalid"):
        _purpose_collection({"purposes": value}, "purposes")


def test_purpose_collection_rejects_duplicates() -> None:
    with pytest.raises(AuthenticationFailed, match="duplicates"):
        _purpose_collection(
            {"purposes": ["people_read", "people_read"]},
            "purposes",
        )


def test_purpose_collection_accepts_tuple_and_normalizes() -> None:
    assert _purpose_collection(
        {"purposes": (" people_read ", "audit_review")},
        "purposes",
    ) == frozenset({"people_read", "audit_review"})


@pytest.mark.parametrize(
    "value",
    [None, 1, "", "x" * 129, "UPPER", "café", "a-b", "people_read\x1f"],
)
def test_purpose_code_rejects_invalid_values(value: object) -> None:
    with pytest.raises(AuthenticationFailed, match="purpose code"):
        _purpose_code(value)


def test_purpose_code_normalizes_valid_ascii_code() -> None:
    assert _purpose_code(" people_read ") == "people_read"


@pytest.mark.parametrize(
    "value",
    [None, b"orgmetra.people.read", "", "x" * 8193, "orgmetra.people.read  orgmetra.people.write", " ".join(f"orgmetra.people.scope{index}" for index in range(65))],
)
def test_scope_collection_rejects_invalid_shape_or_size(value: object) -> None:
    """Reject non-string, empty, oversized, empty-token, and oversized sets."""

    with pytest.raises(AuthenticationFailed, match="scope claim"):
        _scope_collection({"scope": value})


def test_scope_collection_rejects_duplicates_and_accepts_valid_set() -> None:
    """Require unique scope tokens while preserving the validated grant set."""

    with pytest.raises(AuthenticationFailed, match="duplicates"):
        _scope_collection({"scope": "orgmetra.people.read orgmetra.people.read"})
    assert _scope_collection(
        {"scope": "orgmetra.people.read orgmetra.people.write"}
    ) == frozenset({"orgmetra.people.read", "orgmetra.people.write"})


@pytest.mark.parametrize(
    "value",
    [
        None,
        1,
        "",
        "x" * 129,
        "UPPER",
        "café",
        "orgmetra/people/read",
        "orgmetra.people.read\x1f",
    ],
)
def test_scope_code_rejects_invalid_values(value: object) -> None:
    """Reject route or token scopes outside the bounded API vocabulary."""

    with pytest.raises(AuthenticationFailed, match="scope code"):
        _scope_code(value)


def test_scope_code_normalizes_valid_ascii_code() -> None:
    """Normalize harmless surrounding whitespace on a reviewed scope code."""

    assert _scope_code(" orgmetra.people.read ") == "orgmetra.people.read"
