"""Regression tests for independent OAuth capability and HR-purpose checks."""

from __future__ import annotations

from uuid import uuid4

import pytest

from orgmetra_people_api import (
    AuthorizationDenied,
    AuthorizedPrincipal,
    ensure_purpose_authorized,
    ensure_scope_authorized,
)


def _principal(*, scopes: set[str], purposes: set[str]) -> AuthorizedPrincipal:
    """Create one principal with independently controlled capability dimensions."""

    return AuthorizedPrincipal(
        tenant_reference=uuid4(),
        actor_reference=uuid4(),
        allowed_scope_codes=frozenset(scopes),
        allowed_purpose_codes=frozenset(purposes),
    )


def test_valid_purpose_cannot_replace_missing_operation_scope() -> None:
    """Deny write when the token has purpose but only a read capability."""

    principal = _principal(
        scopes={"orgmetra.people.read"},
        purposes={"people_admin"},
    )
    ensure_purpose_authorized(principal, "people_admin")
    with pytest.raises(AuthorizationDenied, match="scope"):
        ensure_scope_authorized(principal, "orgmetra.people.write")


def test_valid_scope_cannot_replace_missing_business_purpose() -> None:
    """Deny write when the token has capability but lacks lawful HR purpose."""

    principal = _principal(
        scopes={"orgmetra.people.write"},
        purposes={"people_read"},
    )
    ensure_scope_authorized(principal, "orgmetra.people.write")
    with pytest.raises(AuthorizationDenied, match="purpose"):
        ensure_purpose_authorized(principal, "people_admin")


@pytest.mark.parametrize(
    "scope_code",
    ["", "Orgmetra.People.Write", "orgmetra/people/write", "orgmetra.people.쓰기"],
)
def test_scope_codes_are_bounded_lower_ascii_machine_codes(scope_code: str) -> None:
    """Reject ambiguous or non-ASCII scope identifiers before authorization."""

    with pytest.raises(ValueError, match="scope"):
        _principal(scopes={scope_code}, purposes={"people_read"})
