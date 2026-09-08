"""Regression contracts for tuple-level principal storage revalidation."""

from __future__ import annotations

import unittest
from uuid import UUID

from orgmetra_people_api import AuthenticatedPrincipal

TENANT = UUID("0198a412-6200-7000-8000-000000000001")
SCOPE = "orgmetra.people.read"


class _TextSubtype(str):
    """Caller-controlled text runtime behavior that cannot become identity evidence."""


class AuthenticatedPrincipalStorageRevalidationTests(unittest.TestCase):
    """Require every public principal view to revalidate tuple-backed evidence."""

    def test_tuple_constructor_bypass_cannot_publish_unvalidated_actor_evidence(self) -> None:
        """A direct base-tuple constructor must not bypass actor runtime validation."""
        forged = tuple.__new__(
            AuthenticatedPrincipal,
            (TENANT.int, _TextSubtype("keyverse:actor-1"), frozenset({SCOPE})),
        )

        with self.assertRaisesRegex(ValueError, "stored authentication evidence"):
            _ = forged.actor_reference

    def test_tuple_constructor_bypass_cannot_publish_unvalidated_scope_evidence(self) -> None:
        """A direct base-tuple constructor must not bypass scope runtime validation."""
        forged = tuple.__new__(
            AuthenticatedPrincipal,
            (TENANT.int, "keyverse:actor-1", frozenset({_TextSubtype(SCOPE)})),
        )

        with self.assertRaisesRegex(ValueError, "stored authentication evidence"):
            _ = forged.granted_scope_codes

    def test_tuple_constructor_bypass_cannot_publish_malformed_storage_shape(self) -> None:
        """Malformed tuple arity must fail through the stable principal integrity contract."""
        forged = tuple.__new__(AuthenticatedPrincipal, (TENANT.int, "keyverse:actor-1"))

        with self.assertRaisesRegex(ValueError, "stored authentication evidence"):
            _ = forged.tenant_record_id

    def test_malformed_storage_cannot_participate_in_value_semantics(self) -> None:
        """Hash, comparison, and repr must not legitimize malformed authentication evidence."""
        forged = tuple.__new__(
            AuthenticatedPrincipal,
            (TENANT.int, object(), frozenset({SCOPE})),
        )
        canonical = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse:actor-1",
            granted_scope_codes=frozenset({SCOPE}),
        )

        with self.assertRaisesRegex(ValueError, "stored authentication evidence"):
            hash(forged)
        with self.assertRaisesRegex(ValueError, "stored authentication evidence"):
            _ = forged == canonical
        with self.assertRaisesRegex(ValueError, "stored authentication evidence"):
            repr(forged)

    def test_malformed_storage_cannot_escape_through_sequence_protocol(self) -> None:
        """Ordinary tuple-like access must not expose raw unvalidated identity evidence."""
        forged = tuple.__new__(
            AuthenticatedPrincipal,
            (TENANT.int, _TextSubtype("keyverse:actor-1"), frozenset({SCOPE})),
        )

        for access in (
            lambda: forged[1],
            lambda: forged[:],
            lambda: list(forged),
            lambda: tuple(forged),
        ):
            with self.subTest(access=access), self.assertRaisesRegex(
                ValueError,
                "stored authentication evidence",
            ):
                access()

    def test_malformed_storage_cannot_escape_through_remaining_tuple_operations(self) -> None:
        """Tuple helpers and operators must validate stored evidence before using it."""
        actor_reference = "keyverse:actor-1"
        forged = tuple.__new__(
            AuthenticatedPrincipal,
            (TENANT.int, _TextSubtype(actor_reference), frozenset({SCOPE})),
        )
        comparison = (TENANT.int, "keyverse:actor-2", frozenset({SCOPE}))

        for access in (
            lambda: len(forged),
            lambda: actor_reference in forged,
            lambda: forged.count(actor_reference),
            lambda: forged.index(actor_reference),
            lambda: forged + (),
            lambda: () + forged,
            lambda: forged * 1,
            lambda: 1 * forged,
            lambda: forged < comparison,
            lambda: forged <= comparison,
            lambda: forged > comparison,
            lambda: forged >= comparison,
        ):
            with self.subTest(access=access), self.assertRaisesRegex(
                ValueError,
                "stored authentication evidence",
            ):
                access()

    def test_valid_tuple_storage_remains_value_compatible_without_claiming_provenance(self) -> None:
        """Valid structural evidence stays readable without treating construction history as authority."""
        structurally_valid = tuple.__new__(
            AuthenticatedPrincipal,
            (TENANT.int, "keyverse:actor-1", frozenset({SCOPE})),
        )
        canonical = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse:actor-1",
            granted_scope_codes=frozenset({SCOPE}),
        )
        expected_storage = (TENANT.int, "keyverse:actor-1", frozenset({SCOPE}))
        comparison = (TENANT.int, "keyverse:actor-2", frozenset({SCOPE}))

        self.assertEqual(structurally_valid.tenant_record_id, TENANT)
        self.assertEqual(structurally_valid.actor_reference, "keyverse:actor-1")
        self.assertEqual(structurally_valid.granted_scope_codes, frozenset({SCOPE}))
        self.assertEqual(structurally_valid[0], TENANT.int)
        self.assertEqual(structurally_valid[1:], expected_storage[1:])
        self.assertEqual(list(structurally_valid), list(expected_storage))
        self.assertEqual(tuple(structurally_valid), expected_storage)
        self.assertEqual(len(structurally_valid), 3)
        self.assertIn("keyverse:actor-1", structurally_valid)
        self.assertEqual(structurally_valid.count("keyverse:actor-1"), 1)
        self.assertEqual(structurally_valid.index("keyverse:actor-1"), 1)
        self.assertEqual(structurally_valid + (), expected_storage)
        self.assertEqual(() + structurally_valid, expected_storage)
        self.assertEqual(structurally_valid * 1, expected_storage)
        self.assertEqual(1 * structurally_valid, expected_storage)
        self.assertLess(structurally_valid, comparison)
        self.assertLessEqual(structurally_valid, comparison)
        self.assertFalse(structurally_valid > comparison)
        self.assertFalse(structurally_valid >= comparison)
        self.assertEqual(structurally_valid, canonical)
        self.assertEqual(hash(structurally_valid), hash(canonical))


if __name__ == "__main__":
    unittest.main()
