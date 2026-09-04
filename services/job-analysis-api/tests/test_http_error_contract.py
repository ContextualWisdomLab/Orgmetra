"""Customer-safe error-envelope regressions for the job-analysis API."""

from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

from orgmetra_job_analysis_api.http import JobAnalysisAsgiApp
from fixtures import ANALYSIS, TENANT, read_policy, write_policy
from test_http_route import FakeAuthenticator, FakeReadPort, FakeWritePort, _api_principal

_SUPPORT_REFERENCE = re.compile(r"^err_[A-Za-z0-9_-]{20,80}$")


class ExplodingAuthenticator:
    """Model an unavailable identity backend with a secret-bearing exception."""

    async def authenticate(self, bearer_token: str) -> object:
        """Fail after receiving a syntactically valid bearer token."""
        del bearer_token
        raise RuntimeError("oidc client_secret=do-not-leak")


class JobAnalysisHttpErrorContractTests(unittest.IsolatedAsyncioTestCase):
    """Keep runtime errors aligned with the published client-safe envelope."""

    def _app(self) -> JobAnalysisAsgiApp:
        """Build a deterministic app for transport-error assertions."""
        return JobAnalysisAsgiApp(
            authenticator=FakeAuthenticator(_api_principal()),
            write_policy=write_policy(),
            read_policy=read_policy(),
            write_port=FakeWritePort(),
            read_port=FakeReadPort(None),
        )

    async def test_route_error_has_actionable_non_disclosing_support_envelope(self) -> None:
        """Return a safe next action and random support handle, not a trace identifier."""
        messages: list[dict[str, object]] = []

        async def receive() -> dict[str, object]:
            raise AssertionError("route rejection must not read a body")

        async def send(message: dict[str, object]) -> None:
            messages.append(message)

        await self._app()(
            {
                "type": "http",
                "method": "POST",
                "path": f"/v1/tenants/{TENANT}/wrong-route",
                "query_string": b"",
                "headers": [],
            },
            receive,
            send,
        )
        start, body = messages
        payload = json.loads(bytes(body["body"]))
        self.assertEqual(start["status"], 404)
        self.assertEqual(payload["error_code"], "route_not_found")
        self.assertEqual(payload["error"], payload["error_code"])
        self.assertTrue(payload["message"])
        self.assertTrue(payload["next_action"])
        self.assertRegex(payload["support_reference"], _SUPPORT_REFERENCE)
        self.assertNotIn(str(TENANT), json.dumps(payload))
        self.assertNotIn("trace", payload["support_reference"].lower())

    async def test_authentication_backend_failure_is_normalized_before_protected_ports(self) -> None:
        """Keep identity-provider failures client-safe and deny downstream data access."""
        write_port = FakeWritePort()
        read_port = FakeReadPort(None)
        app = JobAnalysisAsgiApp(
            authenticator=ExplodingAuthenticator(),
            write_policy=write_policy(),
            read_policy=read_policy(),
            write_port=write_port,
            read_port=read_port,
        )
        messages: list[dict[str, object]] = []

        async def receive() -> dict[str, object]:
            raise AssertionError("GET authentication failure must not read a request body")

        async def send(message: dict[str, object]) -> None:
            messages.append(message)

        await app(
            {
                "type": "http",
                "method": "GET",
                "path": f"/v1/tenants/{TENANT}/job-analysis-snapshots/{ANALYSIS}",
                "query_string": b"",
                "headers": [(b"authorization", b"Bearer opaque-token")],
            },
            receive,
            send,
        )

        start, body = messages
        payload = json.loads(bytes(body["body"]))
        serialized = json.dumps(payload)
        self.assertEqual((start["status"], payload["error_code"]), (500, "internal_error"))
        self.assertEqual(payload["error"], payload["error_code"])
        self.assertRegex(payload["support_reference"], _SUPPORT_REFERENCE)
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("do-not-leak", serialized)
        self.assertEqual(write_port.calls, [])
        self.assertEqual(read_port.calls, [])

    def test_openapi_allows_the_deprecated_error_alias_without_weakening_required_fields(self) -> None:
        """Preserve current clients while requiring the governed four-field envelope."""
        schema = (Path(__file__).resolve().parents[3] / "schemas" / "openapi.yaml").read_text(encoding="utf-8")
        error_schema = schema.split("    ErrorResponse:\n", 1)[1].split(
            "  responses:\n", 1
        )[0]
        for required_field in (
            "error_code",
            "message",
            "next_action",
            "support_reference",
        ):
            self.assertIn(f"        - {required_field}\n", error_schema)
        self.assertIn("        error:\n", error_schema)
        self.assertIn("          deprecated: true\n", error_schema)
        unsupported_response = schema.split("    UnsupportedMediaType:\n", 1)[1]
        self.assertIn("$ref: '#/components/schemas/ErrorResponse'", unsupported_response)


if __name__ == "__main__":
    unittest.main()
