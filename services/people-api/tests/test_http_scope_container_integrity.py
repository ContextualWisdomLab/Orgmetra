"""Fail closed before executable ASGI scope containers reach field access."""

from __future__ import annotations

from datetime import date
import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api import AuthenticatedPrincipal, WorkerPeopleRecord
from orgmetra_people_api.hire import HireAcceptanceCommand, HireAcceptanceResult
from orgmetra_people_api.hire_http import HireAcceptanceAsgiApp
from orgmetra_people_api.http import PeopleAsgiApp

TENANT = UUID("0198a412-7300-7000-8000-000000000001")
PERSON = UUID("0198a412-7300-7000-8000-000000000010")


class _ExplodingScope(dict[str, object]):
    """Expose any scope operation attempted before concrete-container validation."""

    def get(self, key: str, default: object = None) -> object:
        del key, default
        raise AssertionError("scope.get executed before exact built-in dict validation")

    def __getitem__(self, key: str) -> object:
        del key
        raise AssertionError("scope lookup executed before exact built-in dict validation")


class _GuardAuthenticator:
    """Fail if an untrusted outer scope reaches identity resolution."""

    async def authenticate(self, bearer_token: str) -> AuthenticatedPrincipal:
        del bearer_token
        raise AssertionError("untrusted scope reached authentication")


class _GuardReadPort:
    """Fail if an untrusted outer scope reaches protected People persistence."""

    def read_worker(
        self,
        *,
        tenant_record_id: UUID,
        person_record_id: UUID,
        effective_on: date,
    ) -> WorkerPeopleRecord | None:
        del tenant_record_id, person_record_id, effective_on
        raise AssertionError("untrusted scope reached People persistence")


class _GuardHirePort:
    """Fail if an untrusted outer scope reaches confirmed-hire mutation."""

    def accept_hire(
        self,
        *,
        command: HireAcceptanceCommand,
        authorization: object,
    ) -> HireAcceptanceResult:
        del command, authorization
        raise AssertionError("untrusted scope reached confirmed-hire mutation")


class HttpScopeContainerIntegrityTests(unittest.IsolatedAsyncioTestCase):
    """Require the ASGI-specified built-in scope dictionary before any field access."""

    def setUp(self) -> None:
        self.people_policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="scope-container-integrity-v1",
            resource_kind="person_record",
            purpose_code="people_read",
            operation_code="read_record",
            required_scope_code="orgmetra.people.read",
            permitted_fields=frozenset({"display_name"}),
        )
        self.hire_policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="scope-container-integrity-hire-v1",
            resource_kind="selection_decision",
            purpose_code="candidate_hire",
            operation_code="materialize_worker",
            required_scope_code="orgmetra.people.materialize_worker",
            permitted_fields=frozenset({"candidate_worker_conversion"}),
        )

    @staticmethod
    async def _receive() -> dict[str, object]:
        raise AssertionError("untrusted scope reached request-body consumption")

    @staticmethod
    async def _send(message: dict[str, object]) -> None:
        raise AssertionError(f"untrusted scope emitted a response: {message!r}")

    async def test_people_read_rejects_dict_subclass_before_get_or_authentication(self) -> None:
        app = PeopleAsgiApp(
            authenticator=_GuardAuthenticator(),
            policy=self.people_policy,
            read_port=_GuardReadPort(),
        )
        scope = _ExplodingScope(
            {
                "type": "http",
                "method": "GET",
                "path": f"/v1/tenants/{TENANT}/people/{PERSON}",
                "query_string": b"effective_on=2026-09-14&purpose=people_read&fields=display_name",
                "headers": [(b"authorization", b"Bearer opaque-token")],
            }
        )

        with self.assertRaisesRegex(ValueError, "scope must be a built-in dict"):
            await app(scope, self._receive, self._send)

    async def test_confirmed_hire_rejects_dict_subclass_before_get_or_authentication(self) -> None:
        app = HireAcceptanceAsgiApp(
            authenticator=_GuardAuthenticator(),
            policy=self.hire_policy,
            mutation_port=_GuardHirePort(),
        )
        scope = _ExplodingScope(
            {
                "type": "http",
                "method": "POST",
                "path": f"/v1/tenants/{TENANT}/candidate-worker-conversions",
                "query_string": b"purpose=candidate_hire",
                "headers": [(b"authorization", b"Bearer opaque-token")],
            }
        )

        with self.assertRaisesRegex(ValueError, "scope must be a built-in dict"):
            await app(scope, self._receive, self._send)


if __name__ == "__main__":
    unittest.main()
