"""Executable contracts for People API authentication and delegated authorization."""

from __future__ import annotations

import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy
from orgmetra_people_api import AuthenticatedPrincipal, AuthenticationFailed, authorize_resource_fields, extract_bearer_token

TENANT = UUID("0198a412-6000-7000-8000-000000000001")
OTHER_TENANT = UUID("0198a412-6000-7000-8000-000000000002")


class _ExplosiveEquality:
    """Fail if malformed retained UUID evidence reaches equality semantics."""

    def __eq__(self, other: object) -> bool:
        raise AssertionError("forged UUID payload equality must not execute")


class _BehaviorBearingStr(str):
    """Represent a non-exact string that must not cross the authority boundary."""


class _BehaviorBearingAuthorizationHeader(str):
    """Fail if bearer parsing dispatches methods on a non-exact string."""

    def split(self, *args: object, **kwargs: object) -> list[str]:
        raise AssertionError("authorization-header subclass split must not execute")


class _BehaviorBearingFrozenset(frozenset):
    """Fail if a frozenset subclass is iterated during principal validation."""

    def __iter__(self):
        raise AssertionError("scope-container subclass iteration must not execute")


class BearerBoundaryTests(unittest.TestCase):
    """Prove that malformed token syntax never reaches an injected authenticator."""

    def test_accepts_case_insensitive_bearer_scheme(self) -> None:
        self.assertEqual(extract_bearer_token("bEaReR safe-token_123"), "safe-token_123")

    def test_rejects_absent_wrong_or_ambiguous_scheme(self) -> None:
        for header in (None, "", "Basic token", "Bearer", "Bearer one two"):
            with self.subTest(header=header), self.assertRaises(AuthenticationFailed):
                extract_bearer_token(header)

    def test_rejects_behavior_bearing_authorization_header_before_parser_dispatch(self) -> None:
        with self.assertRaises(AuthenticationFailed):
            extract_bearer_token(_BehaviorBearingAuthorizationHeader("Bearer safe-token_123"))

    def test_rejects_hidden_control_non_ascii_and_unbounded_tokens(self) -> None:
        for token in ("bad\x1ftoken", "tökén", "x" * 8193):
            with self.subTest(token_length=len(token)), self.assertRaises(AuthenticationFailed):
                extract_bearer_token(f"Bearer {token}")


class PrincipalBoundaryTests(unittest.TestCase):
    """Keep authenticated identity/scope facts narrow and immutable."""

    def test_rejects_malformed_identity_and_scope_shapes(self) -> None:
        cases = (
            {"tenant_record_id": "tenant-1", "actor_reference": "keyverse:actor-1", "granted_scope_codes": frozenset({"orgmetra.people.read"})},
            {"tenant_record_id": UUID(int=0), "actor_reference": "keyverse:actor-1", "granted_scope_codes": frozenset({"orgmetra.people.read"})},
            {"tenant_record_id": UUID(int=(1 << 128) - 1), "actor_reference": "keyverse:actor-1", "granted_scope_codes": frozenset({"orgmetra.people.read"})},
            {"tenant_record_id": TENANT, "actor_reference": "actor with pii", "granted_scope_codes": frozenset({"orgmetra.people.read"})},
            {"tenant_record_id": TENANT, "actor_reference": "keyverse:actor-1", "granted_scope_codes": set({"orgmetra.people.read"})},
            {"tenant_record_id": TENANT, "actor_reference": "keyverse:actor-1", "granted_scope_codes": frozenset()},
            {"tenant_record_id": TENANT, "actor_reference": "keyverse:actor-1", "granted_scope_codes": frozenset({"orgmetra.*"})},
            {"tenant_record_id": TENANT, "actor_reference": "keyverse:actor-1", "granted_scope_codes": frozenset({1})},
        )
        for values in cases:
            with self.subTest(values=values), self.assertRaises(ValueError):
                AuthenticatedPrincipal(**values)

    def test_rejects_forged_uuid_payload_before_executable_equality(self) -> None:
        forged_tenant = UUID(str(TENANT))
        object.__setattr__(forged_tenant, "int", _ExplosiveEquality())

        with self.assertRaises(ValueError):
            AuthenticatedPrincipal(
                tenant_record_id=forged_tenant,
                actor_reference="keyverse:actor-1",
                granted_scope_codes=frozenset({"orgmetra.people.read"}),
            )

    def test_detaches_tenant_uuid_from_caller_alias(self) -> None:
        caller_tenant = UUID(str(TENANT))
        principal = AuthenticatedPrincipal(
            tenant_record_id=caller_tenant,
            actor_reference="keyverse:actor-1",
            granted_scope_codes=frozenset({"orgmetra.people.read"}),
        )

        object.__setattr__(caller_tenant, "int", OTHER_TENANT.int)

        self.assertEqual(principal.tenant_record_id, TENANT)
        self.assertIsNot(principal.tenant_record_id, caller_tenant)

    def test_tenant_uuid_views_do_not_mutate_retained_principal_authority(self) -> None:
        principal = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse:actor-1",
            granted_scope_codes=frozenset({"orgmetra.people.read"}),
        )
        exposed_tenant = principal.tenant_record_id

        object.__setattr__(exposed_tenant, "int", OTHER_TENANT.int)

        self.assertEqual(principal.tenant_record_id, TENANT)
        self.assertIsNot(principal.tenant_record_id, exposed_tenant)

    def test_revalidates_low_level_retained_principal_storage(self) -> None:
        valid_scopes = frozenset({"orgmetra.people.read"})
        malformed_payloads = (
            (TENANT.int, "keyverse:actor-1"),
            (True, "keyverse:actor-1", valid_scopes),
            (0, "keyverse:actor-1", valid_scopes),
            (TENANT.int, _BehaviorBearingStr("keyverse:actor-1"), valid_scopes),
            (TENANT.int, "keyverse:actor-1", frozenset()),
            (TENANT.int, "keyverse:actor-1", _BehaviorBearingFrozenset(valid_scopes)),
            (TENANT.int, "keyverse:actor-1", frozenset({_BehaviorBearingStr("orgmetra.people.read")})),
        )
        for payload in malformed_payloads:
            forged = tuple.__new__(AuthenticatedPrincipal, payload)
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                _ = forged.tenant_record_id

    def test_rejects_behavior_bearing_text_and_scope_container(self) -> None:
        cases = (
            {
                "tenant_record_id": TENANT,
                "actor_reference": _BehaviorBearingStr("keyverse:actor-1"),
                "granted_scope_codes": frozenset({"orgmetra.people.read"}),
            },
            {
                "tenant_record_id": TENANT,
                "actor_reference": "keyverse:actor-1",
                "granted_scope_codes": frozenset({_BehaviorBearingStr("orgmetra.people.read")}),
            },
            {
                "tenant_record_id": TENANT,
                "actor_reference": "keyverse:actor-1",
                "granted_scope_codes": _BehaviorBearingFrozenset({"orgmetra.people.read"}),
            },
        )
        for values in cases:
            with self.subTest(values=values), self.assertRaises(ValueError):
                AuthenticatedPrincipal(**values)

    def test_principal_contains_no_purpose_grant(self) -> None:
        principal = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse:actor-1",
            granted_scope_codes=frozenset({"orgmetra.people.read"}),
        )
        self.assertFalse(hasattr(principal, "allowed_purpose_codes"))


class DelegatedAuthorizationTests(unittest.TestCase):
    """Prove the service delegates exact-target PII policy decisions."""

    def setUp(self) -> None:
        self.principal = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse:actor-1",
            granted_scope_codes=frozenset({"orgmetra.people.read"}),
        )
        self.policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="v1",
            resource_kind="person_record",
            purpose_code="people_read",
            operation_code="read_record",
            required_scope_code="orgmetra.people.read",
            permitted_fields=frozenset({"display_name"}),
        )

    def test_allows_only_exact_authorized_target_and_field(self) -> None:
        decision = authorize_resource_fields(
            principal=self.principal,
            tenant_record_id=TENANT,
            resource_tenant_record_id=TENANT,
            resource_reference="person_record:0198a412600070008000000000000010",
            purpose_code="people_read",
            operation_code="read_record",
            resource_kind="person_record",
            requested_fields=frozenset({"display_name"}),
            policy=self.policy,
        )
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.resource_reference, "person_record:0198a412600070008000000000000010")
        self.assertEqual(decision.authorized_fields, frozenset({"display_name"}))

    def test_denies_cross_tenant_resource_before_field_release(self) -> None:
        with self.assertRaises(AuthorizationDeniedError) as caught:
            authorize_resource_fields(
                principal=self.principal,
                tenant_record_id=TENANT,
                resource_tenant_record_id=OTHER_TENANT,
                resource_reference="person_record:0198a412600070008000000000000010",
                purpose_code="people_read",
                operation_code="read_record",
                resource_kind="person_record",
                requested_fields=frozenset({"display_name"}),
                policy=self.policy,
            )
        self.assertEqual(caught.exception.reason_code, "tenant_scope_mismatch")

    def test_denies_when_operation_scope_is_missing_even_with_valid_purpose(self) -> None:
        principal = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse:actor-1",
            granted_scope_codes=frozenset({"orgmetra.audit.read"}),
        )
        with self.assertRaises(AuthorizationDeniedError) as caught:
            authorize_resource_fields(
                principal=principal,
                tenant_record_id=TENANT,
                resource_tenant_record_id=TENANT,
                resource_reference="person_record:0198a412600070008000000000000010",
                purpose_code="people_read",
                operation_code="read_record",
                resource_kind="person_record",
                requested_fields=frozenset({"display_name"}),
                policy=self.policy,
            )
        self.assertEqual(caught.exception.reason_code, "required_scope_missing")


if __name__ == "__main__":
    unittest.main()
