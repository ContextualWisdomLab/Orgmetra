"""Fail-closed regressions for malformed identity-adapter return values."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

from orgmetra_people_api import AuthenticatedPrincipal


_SUPPORT_PATH = Path(__file__).with_name("test_support_reference_correlation.py")
_SPEC = importlib.util.spec_from_file_location("orgmetra_authenticator_contract_fixtures", _SUPPORT_PATH)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover - import machinery invariant
    raise RuntimeError("authenticator regression fixtures could not be loaded")
_SUPPORT = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_SUPPORT)


class _MalformedPrincipal:
    """Carry a backend secret in representation to prove it never crosses the boundary."""

    def __repr__(self) -> str:
        return "identity-backend secret=must-not-leak"


class MalformedPrincipalAuthenticator:
    """Satisfy the runtime protocol while violating its annotated return contract."""

    async def authenticate(self, bearer_token: str) -> AuthenticatedPrincipal:
        if bearer_token != "opaque-token":
            raise AssertionError("unexpected bearer token")
        return _MalformedPrincipal()  # type: ignore[return-value]


class AuthenticatorPrincipalContractTests(unittest.IsolatedAsyncioTestCase):
    """Contain malformed authenticated identities before body parsing or policy use."""

    def setUp(self) -> None:
        self.fixtures = _SUPPORT.SupportReferenceCorrelationTests()
        self.fixtures.setUp()

    async def _invoke_without_escape(
        self,
        app: object,
        *,
        scope: dict[str, object],
    ) -> tuple[int, dict[str, object]]:
        try:
            return await _SUPPORT.invoke_without_body_read(app, scope=scope)
        except Exception as error:  # noqa: BLE001 - escaped boundary failures are the regression under test.
            raise AssertionError(
                f"malformed authenticator result escaped ASGI boundary as {type(error).__name__}"
            ) from error

    def _assert_sanitized_failure(
        self,
        *,
        status: int,
        response: dict[str, object],
        captured: object,
    ) -> None:
        self.assertEqual(status, 500)
        self.assertEqual(response["error_code"], "internal_error")
        records = captured.records  # type: ignore[attr-defined]
        output = captured.output  # type: ignore[attr-defined]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].support_reference, response["support_reference"])
        serialized = json.dumps(response, sort_keys=True)
        log_text = " ".join(output)
        for secret in ("must-not-leak", "opaque-token"):
            self.assertNotIn(secret, serialized)
            self.assertNotIn(secret, log_text)

    async def test_confirmed_hire_malformed_principal_is_sanitized_without_body_read(self) -> None:
        app = _SUPPORT.HireAcceptanceAsgiApp(
            authenticator=MalformedPrincipalAuthenticator(),
            policy=self.fixtures._hire_policy(),
            mutation_port=_SUPPORT.FailingHirePort(),
        )
        with self.assertLogs("orgmetra_people_api.hire_http", level="ERROR") as captured:
            status, response = await self._invoke_without_escape(
                app,
                scope={
                    "type": "http",
                    "method": "POST",
                    "path": f"/v1/tenants/{_SUPPORT.TENANT}/candidate-worker-conversions",
                    "query_string": b"purpose=candidate_hire",
                    "headers": [(b"authorization", b"Bearer opaque-token")],
                },
            )
        self._assert_sanitized_failure(status=status, response=response, captured=captured)

    async def test_people_mutation_malformed_principal_is_sanitized_without_body_read(self) -> None:
        app = _SUPPORT.PeopleMutationAsgiApp(
            authenticator=MalformedPrincipalAuthenticator(),
            employment_policy=self.fixtures._employment_policy(),
            position_policy=self.fixtures._position_policy(),
            assignment_policy=self.fixtures._assignment_policy(),
            mutation_port=_SUPPORT.FailingPeopleMutationPort(),
            id_factory=_SUPPORT.SequentialIdFactory(),
        )
        with self.assertLogs("orgmetra_people_api.mutation_http", level="ERROR") as captured:
            status, response = await self._invoke_without_escape(
                app,
                scope={
                    "type": "http",
                    "method": "POST",
                    "path": "/v1/employment-records",
                    "query_string": b"",
                    "headers": [
                        (b"authorization", b"Bearer opaque-token"),
                        (b"content-type", b"application/json"),
                        (b"idempotency-key", b"malformed-principal-people-99"),
                        (b"x-tenant-reference", str(_SUPPORT.TENANT).encode("ascii")),
                        (b"x-actor-reference", b"keyverse_subject:operator-99"),
                        (b"x-purpose-code", b"workforce_admin"),
                    ],
                },
            )
        self._assert_sanitized_failure(status=status, response=response, captured=captured)


if __name__ == "__main__":
    unittest.main()
