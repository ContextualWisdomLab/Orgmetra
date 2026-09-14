"""Adversarial outer request-metadata integrity for Employment separation HTTP."""

from __future__ import annotations

import unittest

from orgmetra_people_api.separation_http import EmploymentSeparationAsgiApp
from test_employment_separation_http import EmploymentSeparationHttpTests, ROUTE


class _ExecutableScope(dict[str, object]):
    """Tripwire for scope behavior before the exact ASGI container gate."""

    calls = 0

    def get(self, key: str, default: object = None) -> object:
        type(self).calls += 1
        raise TypeError("scope.get executed before exact scope validation")


class _ExecutableString(str):
    """Tripwire for equality behavior before exact route-scalar validation."""

    calls = 0

    def __eq__(self, other: object) -> bool:
        type(self).calls += 1
        raise TypeError("string equality executed before exact scalar validation")

    def __ne__(self, other: object) -> bool:
        type(self).calls += 1
        raise TypeError("string inequality executed before exact scalar validation")


class EmploymentSeparationHttpRequestMetadataIntegrityTests(unittest.IsolatedAsyncioTestCase):
    """Require inert outer ASGI metadata before separation routing behavior executes."""

    async def test_scope_subclass_is_rejected_before_get_executes(self) -> None:
        """The outer ASGI scope must be an exact dict before any mapping method runs."""
        app = object.__new__(EmploymentSeparationAsgiApp)
        scope = _ExecutableScope({"type": "http"})
        _ExecutableScope.calls = 0

        async def receive() -> dict[str, object]:
            raise AssertionError("body must not be read")

        async def send(message: dict[str, object]) -> None:
            raise AssertionError(f"response must not be sent: {message}")

        with self.assertRaisesRegex(ValueError, "exact ASGI scope"):
            await app(scope, receive, send)
        self.assertEqual(_ExecutableScope.calls, 0)

    async def test_method_subclass_is_rejected_before_equality_executes(self) -> None:
        """A method subtype must route to 405 without caller-defined equality behavior."""
        support = EmploymentSeparationHttpTests(
            methodName="test_route_method_and_purpose_fail_without_persistence"
        )
        support.setUp()
        _ExecutableString.calls = 0

        status, _headers, payload = await support._request(
            support._app(),
            method=_ExecutableString("POST"),
        )

        self.assertEqual(status, 405)
        self.assertEqual(payload["error_code"], "method_not_allowed")
        self.assertEqual(_ExecutableString.calls, 0)

    async def test_path_subclass_is_rejected_before_equality_executes(self) -> None:
        """A path subtype must route to 404 without caller-defined equality behavior."""
        support = EmploymentSeparationHttpTests(
            methodName="test_route_method_and_purpose_fail_without_persistence"
        )
        support.setUp()
        _ExecutableString.calls = 0

        status, _headers, payload = await support._request(
            support._app(),
            path=_ExecutableString(ROUTE),
        )

        self.assertEqual(status, 404)
        self.assertEqual(payload["error_code"], "route_not_found")
        self.assertEqual(_ExecutableString.calls, 0)


if __name__ == "__main__":
    unittest.main()
