"""Regression contract for exact UUID payload validation before sentinel comparison."""

from __future__ import annotations

from uuid import UUID

import pytest

from orgmetra_workforce_validation_api.registry import ValidationPrincipal


class _ExecutableUUIDPayload:
    """Fail if validation compares a forged UUID payload before proving it is an int."""

    def __eq__(self, other: object) -> bool:
        """Expose equality execution as a trust-boundary violation."""
        raise AssertionError(f"forged UUID payload executed equality against {other!r}")


def test_exact_uuid_with_executable_internal_payload_fails_before_comparison() -> None:
    """Exact UUID outer type cannot authorize executable non-integer internal storage."""
    tenant_record_id = UUID("10000000-0000-7000-8000-000000000001")
    object.__setattr__(tenant_record_id, "int", _ExecutableUUIDPayload())

    with pytest.raises(ValueError, match="tenant_record_id must be an exact operational UUID"):
        ValidationPrincipal(
            tenant_record_id=tenant_record_id,
            actor_reference="person:analyst-1",
            granted_scope_codes=frozenset({"orgmetra.workforce_validation.read"}),
        )
