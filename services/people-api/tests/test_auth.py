"""Unit tests for the people API authentication boundary."""

from __future__ import annotations

from uuid import uuid4

import pytest

from orgmetra_people_api import (
    AuthenticationFailed,
    AuthorizationDenied,
    AuthorizedPrincipal,
    ensure_purpose_authorized,
    extract_bearer_token,
)


def _principal(*purposes: str) -> AuthorizedPrincipal:
    """Create one principal for purpose-authorization tests."""

    return AuthorizedPrincipal(
        tenant_reference=uuid4(),
        actor_reference=uuid4(),
        allowed_purpose_codes=frozenset(purposes),
    )


def test_principal_normalizes_valid_purposes() -> None:
    principal = _principal(" people_read ", "audit_review")

    assert principal.allowed_purpose_codes == frozenset(
        {"people_read", "audit_review"}
    )


def test_principal_rejects_empty_purpose_collection() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        _principal()


@pytest.mark.parametrize(
    "purpose_code",
    ["", " ", "UPPER", "people-read", "café", "x" * 129],
)
def test_principal_rejects_invalid_purpose_codes(purpose_code: str) -> None:
    with pytest.raises(ValueError, match="purpose code"):
        _principal(purpose_code)


def test_extract_bearer_token_accepts_case_insensitive_scheme() -> None:
    assert extract_bearer_token("bEaReR safe-token_123") == "safe-token_123"


@pytest.mark.parametrize(
    "header",
    [None, "", "Basic token", "Bearer", "Bearer one two"],
)
def test_extract_bearer_token_rejects_missing_or_malformed_header(
    header: str | None,
) -> None:
    with pytest.raises(AuthenticationFailed):
        extract_bearer_token(header)


@pytest.mark.parametrize(
    "token",
    ["x" * 8193, "bad\x1ftoken", "tökén"],
)
def test_extract_bearer_token_rejects_unbounded_or_non_ascii_token(token: str) -> None:
    with pytest.raises(AuthenticationFailed, match="token"):
        extract_bearer_token(f"Bearer {token}")


def test_ensure_purpose_authorized_accepts_allowed_purpose() -> None:
    ensure_purpose_authorized(_principal("people_read"), " people_read ")


def test_ensure_purpose_authorized_rejects_missing_purpose() -> None:
    with pytest.raises(AuthorizationDenied, match="not authorized"):
        ensure_purpose_authorized(_principal("people_read"), "people_admin")
