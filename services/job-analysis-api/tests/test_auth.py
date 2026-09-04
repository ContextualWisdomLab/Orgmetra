"""Executable contracts for job-analysis authentication and delegated authorization."""

from __future__ import annotations

import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import AuthorizationDeniedError

from orgmetra_job_analysis_api import (
    AuthenticatedPrincipal,
    AuthenticationFailed,
    authorize_resource_fields,
    extract_bearer_token,
)
from fixtures import TENANT, OTHER_TENANT, ANALYSIS, write_policy


class _ExecutableHeader(str):
    """Model caller-defined header text that executes during polymorphic parsing."""

    def split(self, *args: object, **kwargs: object) -> list[str]:
        raise AssertionError("executable header split must not run")


class BearerBoundaryTests(unittest.TestCase):
    """Prove that malformed token syntax never reaches an injected authenticator."""

    def test_accepts_case_insensitive_bearer_scheme(self) -> None:
        self.assertEqual(extract_bearer_token("bEaReR safe-token_123"), "safe-token_123")

    def test_rejects_absent_wrong_or_ambiguous_scheme(self) -> None:
        for header in (None, "", "Basic token", "Bearer", "Bearer one two"):
            with self.subTest(header=header), self.assertRaises(AuthenticationFailed):
                extract_bearer_token(header)

    def test_rejects_hidden_control_non_ascii_and_unbounded_tokens(self) -> None:
        for token in ("bad\x1ftoken", "tökén", "x" * 8193):
            with self.subTest(token_length=len(token)), self.assertRaises(AuthenticationFailed):
                extract_bearer_token(f"Bearer {token}")

    def test_rejects_executable_string_subtype_before_parsing(self) -> None:
        with self.assertRaisesRegex(AuthenticationFailed, "authorization header"):
            extract_bearer_token(_ExecutableHeader("Bearer forged-token"))


class PrincipalBoundaryTests(unittest.TestCase):
    """Keep authenticated identity/scope facts narrow and immutable."""

    def test_rejects_malformed_identity_and_scope_shapes(self) -> None:
        cases = (
            {"tenant_record_id": "tenant-1", "actor_reference": "keyverse:actor-1", "granted_scope_codes": frozenset({"orgmetra.job_architecture.write"})},
            {"tenant_record_id": UUID(int=0), "actor_reference": "keyverse:actor-1", "granted_scope_codes": frozenset({"orgmetra.job_architecture.write"})},
            {"tenant_record_id": UUID(int=(1 << 128) - 1), "actor_reference": "keyverse:actor-1", "granted_scope_codes": frozenset({"orgmetra.job_architecture.write"})},
            {"tenant_record_id": TENANT, "actor_reference": "actor with pii", "granted_scope_codes": frozenset({"orgmetra.job_architecture.write"})},
            {"tenant_record_id": TENANT, "actor_reference": "keyverse:actor-1", "granted_scope_codes": set({"orgmetra.job_architecture.write"})},
            {"tenant_record_id": TENANT, "actor_reference": "keyverse:actor-1", "granted_scope_codes": frozenset()},
            {"tenant_record_id": TENANT, "actor_reference": "keyverse:actor-1", "granted_scope_codes": frozenset({"orgmetra.*"})},
            {"tenant_record_id": TENANT, "actor_reference": "keyverse:actor-1", "granted_scope_codes": frozenset({1})},
        )
        for values in cases:
            with self.subTest(values=values), self.assertRaises(ValueError):
                AuthenticatedPrincipal(**values)

    def test_principal_contains_no_purpose_grant(self) -> None:
        principal = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse:actor-1",
            granted_scope_codes=frozenset({"orgmetra.job_architecture.write"}),
        )
        self.assertFalse(hasattr(principal, "allowed_purpose_codes"))


class DelegatedAuthorizationTests(unittest.TestCase):
    """Prove the service delegates exact-target job-analysis policy decisions."""

    def test_allows_only_exact_authorized_target(self) -> None:
        principal = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse:actor-1",
            granted_scope_codes=frozenset({"orgmetra.job_architecture.write"}),
        )
        decision = authorize_resource_fields(
            principal=principal,
            tenant_record_id=TENANT,
            resource_tenant_record_id=TENANT,
            resource_reference=f"job_analysis_snapshot:{ANALYSIS.hex}",
            purpose_code="job_analysis_write",
            operation_code="write_record",
            resource_kind="job_analysis_snapshot",
            requested_fields=frozenset({"tasks", "idempotency_key"}),
            policy=write_policy(),
        )
        self.assertTrue(decision.allowed)

    def test_denies_cross_tenant_resource(self) -> None:
        principal = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse:actor-1",
            granted_scope_codes=frozenset({"orgmetra.job_architecture.write"}),
        )
        with self.assertRaises(AuthorizationDeniedError) as caught:
            authorize_resource_fields(
                principal=principal,
                tenant_record_id=TENANT,
                resource_tenant_record_id=OTHER_TENANT,
                resource_reference=f"job_analysis_snapshot:{ANALYSIS.hex}",
                purpose_code="job_analysis_write",
                operation_code="write_record",
                resource_kind="job_analysis_snapshot",
                requested_fields=frozenset({"tasks"}),
                policy=write_policy(),
            )
        self.assertEqual(caught.exception.reason_code, "tenant_scope_mismatch")


if __name__ == "__main__":
    unittest.main()
