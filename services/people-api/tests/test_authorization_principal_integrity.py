"""Principal-evidence integrity at the shared People authorization boundary."""

from __future__ import annotations

import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.authorization import authorize_resource_fields

TENANT = UUID("0198a412-9200-7000-8000-000000000001")


class _HostilePrincipal(AuthenticatedPrincipal):
    """Expose behavior if shared authorization trusts a principal subtype."""

    property_reads = 0

    @property
    def tenant_record_id(self) -> UUID:
        type(self).property_reads += 1
        raise AssertionError("principal subtype property must not execute")


class _ExecutableUuidPayload:
    """Fail if forged UUID payload participates in trust-bearing comparison."""

    comparisons = 0

    def __eq__(self, other: object) -> bool:
        type(self).comparisons += 1
        raise AssertionError("forged UUID payload must not participate in comparison")

    def __lt__(self, other: object) -> bool:
        type(self).comparisons += 1
        raise AssertionError("forged UUID payload must not participate in ordering")

    def __gt__(self, other: object) -> bool:
        type(self).comparisons += 1
        raise AssertionError("forged UUID payload must not participate in ordering")


class _TextSubtype(str):
    """Represent behavior-bearing text that must not become policy evidence."""


class AuthorizationPrincipalIntegrityTests(unittest.TestCase):
    """Require direct application callers to supply inert authenticated evidence."""

    def setUp(self) -> None:
        _HostilePrincipal.property_reads = 0
        _ExecutableUuidPayload.comparisons = 0
        self.policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="v1",
            resource_kind="employment_record",
            purpose_code="workforce_admin",
            operation_code="separate_record",
            required_scope_code="orgmetra.people.write",
            permitted_fields=frozenset({"employment_record"}),
        )

    def _authorize(self, principal: AuthenticatedPrincipal) -> object:
        return authorize_resource_fields(
            principal=principal,
            tenant_record_id=TENANT,
            resource_tenant_record_id=TENANT,
            resource_reference="employment_record:0198a412920070008000000000000010",
            purpose_code="workforce_admin",
            operation_code="separate_record",
            resource_kind="employment_record",
            requested_fields=frozenset({"employment_record"}),
            policy=self.policy,
        )

    def test_principal_subclass_fails_before_property_access(self) -> None:
        principal = object.__new__(_HostilePrincipal)
        AuthenticatedPrincipal.__dict__["tenant_record_id"].__set__(principal, TENANT)
        AuthenticatedPrincipal.__dict__["actor_reference"].__set__(principal, "keyverse:operator-17")
        AuthenticatedPrincipal.__dict__["granted_scope_codes"].__set__(
            principal,
            frozenset({"orgmetra.people.write"}),
        )

        with self.assertRaisesRegex(TypeError, "AuthenticatedPrincipal"):
            self._authorize(principal)

        self.assertEqual(_HostilePrincipal.property_reads, 0)

    def test_nested_uuid_payload_fails_before_comparison(self) -> None:
        principal = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse:operator-17",
            granted_scope_codes=frozenset({"orgmetra.people.write"}),
        )
        object.__setattr__(principal.tenant_record_id, "int", _ExecutableUuidPayload())

        with self.assertRaisesRegex(TypeError, "tenant_record_id"):
            self._authorize(principal)

        self.assertEqual(_ExecutableUuidPayload.comparisons, 0)

    def test_nested_actor_and_scope_text_subtypes_fail_closed(self) -> None:
        actor = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference=_TextSubtype("keyverse:operator-17"),
            granted_scope_codes=frozenset({"orgmetra.people.write"}),
        )
        with self.assertRaisesRegex(TypeError, "actor_reference"):
            self._authorize(actor)

        scope = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse:operator-17",
            granted_scope_codes=frozenset({_TextSubtype("orgmetra.people.write")}),
        )
        with self.assertRaisesRegex(TypeError, "granted_scope_codes"):
            self._authorize(scope)

    def test_exact_principal_preserves_existing_keyverse_decision(self) -> None:
        principal = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse:operator-17",
            granted_scope_codes=frozenset({"orgmetra.people.write"}),
        )

        decision = self._authorize(principal)

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.actor_reference, "keyverse:operator-17")
        self.assertEqual(decision.tenant_record_id, TENANT)
        self.assertEqual(decision.authorized_fields, frozenset({"employment_record"}))


if __name__ == "__main__":
    unittest.main()
