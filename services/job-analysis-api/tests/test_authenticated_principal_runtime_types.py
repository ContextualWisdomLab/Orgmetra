"""Regression contracts for Job Analysis principal runtime-type integrity."""

from __future__ import annotations

import unittest
from uuid import UUID

from orgmetra_job_analysis_api import AuthenticatedPrincipal

TENANT = UUID("0198a412-6000-7000-8000-000000000001")
OTHER_TENANT = UUID("0198a412-6000-7000-8000-000000000002")
SCOPE = "orgmetra.job_architecture.write"


class _UUIDSubtype(UUID):
    """Caller-defined UUID subtype that must not cross the authentication boundary."""


class _TextSubtype(str):
    """Caller-defined text subtype that must not carry identity or scope evidence."""


class _ScopeSetSubtype(frozenset[str]):
    """Caller-defined immutable-set subtype that must not carry scope evidence."""


class AuthenticatedPrincipalRuntimeTypeTests(unittest.TestCase):
    """Require exact canonical authentication evidence at principal construction."""

    def test_rejects_trust_bearing_runtime_subtypes(self) -> None:
        cases = (
            {
                "tenant_record_id": _UUIDSubtype(TENANT.hex),
                "actor_reference": "keyverse:actor-ja-1",
                "granted_scope_codes": frozenset({SCOPE}),
            },
            {
                "tenant_record_id": TENANT,
                "actor_reference": _TextSubtype("keyverse:actor-ja-1"),
                "granted_scope_codes": frozenset({SCOPE}),
            },
            {
                "tenant_record_id": TENANT,
                "actor_reference": "keyverse:actor-ja-1",
                "granted_scope_codes": _ScopeSetSubtype({SCOPE}),
            },
            {
                "tenant_record_id": TENANT,
                "actor_reference": "keyverse:actor-ja-1",
                "granted_scope_codes": frozenset({_TextSubtype(SCOPE)}),
            },
        )
        for values in cases:
            with self.subTest(values=values), self.assertRaises(ValueError):
                AuthenticatedPrincipal(**values)

    def test_principal_runtime_class_cannot_be_subclassed(self) -> None:
        """Executable principal subclasses cannot override authenticated evidence access."""
        with self.assertRaisesRegex(TypeError, "AuthenticatedPrincipal must not be subclassed"):

            class _PrincipalSubtype(AuthenticatedPrincipal):
                pass

    def test_tenant_uuid_is_detached_from_caller_owned_instance(self) -> None:
        """Post-construction mutation of the caller UUID cannot retarget the principal."""
        tenant_record_id = UUID(TENANT.hex)
        principal = AuthenticatedPrincipal(
            tenant_record_id=tenant_record_id,
            actor_reference="keyverse:actor-ja-1",
            granted_scope_codes=frozenset({SCOPE}),
        )

        object.__setattr__(tenant_record_id, "int", OTHER_TENANT.int)

        self.assertEqual(principal.tenant_record_id, TENANT)
        self.assertIsNot(principal.tenant_record_id, tenant_record_id)

    def test_principal_evidence_cannot_be_rewritten_after_authentication(self) -> None:
        """Low-level writes must not replace authenticated evidence on a live principal."""
        principal = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse:actor-ja-1",
            granted_scope_codes=frozenset({SCOPE}),
        )
        cases = (
            ("tenant_record_id", OTHER_TENANT),
            ("actor_reference", "keyverse:actor-ja-2"),
            ("granted_scope_codes", frozenset({"orgmetra.job_architecture.read"})),
        )

        for field_name, replacement in cases:
            with self.subTest(field_name=field_name), self.assertRaises((AttributeError, TypeError)):
                object.__setattr__(principal, field_name, replacement)

        self.assertEqual(principal.tenant_record_id, TENANT)
        self.assertEqual(principal.actor_reference, "keyverse:actor-ja-1")
        self.assertEqual(principal.granted_scope_codes, frozenset({SCOPE}))

    def test_rejects_corrupted_exact_uuid_state(self) -> None:
        """An exact UUID with an invalid internal integer cannot become identity evidence."""
        tenant_record_id = UUID(TENANT.hex)
        object.__setattr__(tenant_record_id, "int", "not-an-integer")

        with self.assertRaisesRegex(ValueError, "tenant_record_id must contain a valid UUID integer"):
            AuthenticatedPrincipal(
                tenant_record_id=tenant_record_id,
                actor_reference="keyverse:actor-ja-1",
                granted_scope_codes=frozenset({SCOPE}),
            )


if __name__ == "__main__":
    unittest.main()
