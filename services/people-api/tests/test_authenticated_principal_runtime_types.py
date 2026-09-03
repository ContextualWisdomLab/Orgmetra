"""Regression contracts for authenticated principal runtime-type integrity."""

from __future__ import annotations

import unittest
from uuid import UUID

from orgmetra_people_api import AuthenticatedPrincipal

TENANT = UUID("0198a412-6000-7000-8000-000000000001")
SCOPE = "orgmetra.people.read"


class _UUIDSubtype(UUID):
    """Caller-defined UUID subtype that must not cross the authentication boundary."""


class _TextSubtype(str):
    """Caller-defined text subtype that must not carry identity or scope evidence."""


class _ScopeSetSubtype(frozenset[str]):
    """Caller-defined immutable-set subtype that must not carry scope evidence."""


class AuthenticatedPrincipalRuntimeTypeTests(unittest.TestCase):
    """Require exact built-in trust-bearing values at principal construction."""

    def test_rejects_trust_bearing_runtime_subtypes(self) -> None:
        cases = (
            {
                "tenant_record_id": _UUIDSubtype(TENANT.hex),
                "actor_reference": "keyverse:actor-1",
                "granted_scope_codes": frozenset({SCOPE}),
            },
            {
                "tenant_record_id": TENANT,
                "actor_reference": _TextSubtype("keyverse:actor-1"),
                "granted_scope_codes": frozenset({SCOPE}),
            },
            {
                "tenant_record_id": TENANT,
                "actor_reference": "keyverse:actor-1",
                "granted_scope_codes": _ScopeSetSubtype({SCOPE}),
            },
            {
                "tenant_record_id": TENANT,
                "actor_reference": "keyverse:actor-1",
                "granted_scope_codes": frozenset({_TextSubtype(SCOPE)}),
            },
        )
        for values in cases:
            with self.subTest(values=values), self.assertRaises(ValueError):
                AuthenticatedPrincipal(**values)


if __name__ == "__main__":
    unittest.main()
