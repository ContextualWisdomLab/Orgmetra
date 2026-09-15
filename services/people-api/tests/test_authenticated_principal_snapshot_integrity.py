"""Authenticated-principal snapshot integrity for high-impact People write routes."""

from __future__ import annotations

import unittest
from uuid import UUID

from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.mutation_http import _detach_authenticated_principal

TENANT = UUID("0198a412-9100-7000-8000-000000000001")


class _HostilePrincipal(AuthenticatedPrincipal):
    """Expose behavior if a subtype is trusted before exact representation validation."""

    property_reads = 0

    @property
    def tenant_record_id(self) -> UUID:
        type(self).property_reads += 1
        raise AssertionError("principal subtype property must not execute")


class _ExecutableUuidPayload:
    """Fail if UUID sentinel/range logic executes behavior before exact scalar proof."""

    comparisons = 0

    def __eq__(self, other: object) -> bool:
        type(self).comparisons += 1
        raise TypeError("forged UUID payload must not participate in comparison")

    def __lt__(self, other: object) -> bool:
        type(self).comparisons += 1
        raise TypeError("forged UUID payload must not participate in ordering")

    def __le__(self, other: object) -> bool:
        type(self).comparisons += 1
        raise TypeError("forged UUID payload must not participate in ordering")

    def __gt__(self, other: object) -> bool:
        type(self).comparisons += 1
        raise TypeError("forged UUID payload must not participate in ordering")

    def __ge__(self, other: object) -> bool:
        type(self).comparisons += 1
        raise TypeError("forged UUID payload must not participate in ordering")


class _TextSubtype(str):
    """Represent behavior-bearing text that must not cross the trust boundary."""


class AuthenticatedPrincipalSnapshotIntegrityTests(unittest.TestCase):
    """Require identity-backend evidence to become inert owned authority immediately."""

    def setUp(self) -> None:
        _HostilePrincipal.property_reads = 0
        _ExecutableUuidPayload.comparisons = 0

    def test_principal_subclass_is_rejected_before_property_access(self) -> None:
        principal = object.__new__(_HostilePrincipal)
        AuthenticatedPrincipal.__dict__["tenant_record_id"].__set__(principal, TENANT)
        AuthenticatedPrincipal.__dict__["actor_reference"].__set__(
            principal,
            "keyverse_subject:people-operator-17",
        )
        AuthenticatedPrincipal.__dict__["granted_scope_codes"].__set__(
            principal,
            frozenset({"orgmetra.people.write"}),
        )

        with self.assertRaisesRegex(TypeError, "AuthenticatedPrincipal"):
            _detach_authenticated_principal(principal)

        self.assertEqual(_HostilePrincipal.property_reads, 0)

    def test_nested_uuid_payload_is_rejected_before_comparison(self) -> None:
        principal = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse_subject:people-operator-17",
            granted_scope_codes=frozenset({"orgmetra.people.write"}),
        )
        object.__setattr__(principal.tenant_record_id, "int", _ExecutableUuidPayload())

        with self.assertRaisesRegex(TypeError, "tenant_record_id"):
            _detach_authenticated_principal(principal)

        self.assertEqual(_ExecutableUuidPayload.comparisons, 0)

    def test_nested_text_and_scope_subtypes_fail_closed(self) -> None:
        actor = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference=_TextSubtype("keyverse_subject:people-operator-17"),
            granted_scope_codes=frozenset({"orgmetra.people.write"}),
        )
        with self.assertRaisesRegex(TypeError, "actor_reference"):
            _detach_authenticated_principal(actor)

        scope = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse_subject:people-operator-17",
            granted_scope_codes=frozenset({_TextSubtype("orgmetra.people.write")}),
        )
        with self.assertRaisesRegex(TypeError, "granted_scope_codes"):
            _detach_authenticated_principal(scope)

    def test_valid_principal_is_detached_from_authenticator_owned_uuid(self) -> None:
        principal = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse_subject:people-operator-17",
            granted_scope_codes=frozenset({"orgmetra.people.write"}),
        )

        detached = _detach_authenticated_principal(principal)

        self.assertIs(type(detached), AuthenticatedPrincipal)
        self.assertIsNot(detached, principal)
        self.assertEqual(detached.tenant_record_id, TENANT)
        self.assertIsNot(detached.tenant_record_id, principal.tenant_record_id)
        self.assertEqual(detached.actor_reference, principal.actor_reference)
        self.assertEqual(detached.granted_scope_codes, principal.granted_scope_codes)

        object.__setattr__(principal.tenant_record_id, "int", TENANT.int + 1)
        self.assertEqual(detached.tenant_record_id, TENANT)


if __name__ == "__main__":
    unittest.main()
