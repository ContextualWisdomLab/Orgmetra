"""Adversarial request-metadata integrity for generic People mutation HTTP."""

from __future__ import annotations

import unittest

from orgmetra_people_api.mutation_http import (
    PeopleMutationAsgiApp,
    _InvalidHttpRequest,
    _mutation_route,
    _parse_command_headers,
)


class _ExecutableScope(dict[str, object]):
    """Tripwire for scope behavior before the exact ASGI container gate."""

    calls = 0

    def get(self, key: str, default: object = None) -> object:
        type(self).calls += 1
        raise TypeError("scope.get executed before exact scope validation")


class _ExecutablePath(str):
    """Tripwire for route string behavior before exact scalar validation."""

    calls = 0

    def strip(self, chars: str | None = None) -> str:
        type(self).calls += 1
        raise TypeError("path.strip executed before exact path validation")


class _ExecutableHeaders(list[tuple[bytes, bytes]]):
    """Tripwire for header collection iteration before exact container validation."""

    calls = 0

    def __iter__(self):
        type(self).calls += 1
        raise TypeError("header collection iterated before exact validation")


class _ExecutableHeaderRow(tuple[bytes, bytes]):
    """Tripwire for header row length before exact row validation."""

    calls = 0

    def __len__(self) -> int:
        type(self).calls += 1
        raise TypeError("header row length read before exact validation")


class _ExecutableBytes(bytes):
    """Tripwire for header byte behavior before exact scalar validation."""

    calls = 0

    def lower(self) -> bytes:
        type(self).calls += 1
        raise TypeError("header bytes lowered before exact validation")


def _required_headers() -> list[tuple[bytes, bytes]]:
    """Return the minimal valid command metadata used by focused parser tests."""
    return [
        (b"idempotency-key", b"idempotency-key-17xx"),
        (b"x-tenant-reference", b"0198a412-8100-7000-8000-000000000001"),
        (b"x-actor-reference", b"keyverse_subject:operator-17"),
        (b"x-purpose-code", b"workforce_admin"),
    ]


class MutationRequestMetadataIntegrityTests(unittest.IsolatedAsyncioTestCase):
    """Require inert bounded ASGI metadata before generic mutation behavior executes."""

    async def test_scope_subclass_is_rejected_before_get_executes(self) -> None:
        """The outer ASGI scope must be an exact dict before any mapping method runs."""
        app = object.__new__(PeopleMutationAsgiApp)
        scope = _ExecutableScope({"type": "http"})
        _ExecutableScope.calls = 0

        async def receive() -> dict[str, object]:
            raise AssertionError("body must not be read")

        async def send(message: dict[str, object]) -> None:
            raise AssertionError(f"response must not be sent: {message}")

        with self.assertRaisesRegex(ValueError, "exact ASGI scope"):
            await app(scope, receive, send)
        self.assertEqual(_ExecutableScope.calls, 0)

    def test_path_subclass_is_rejected_before_string_methods_execute(self) -> None:
        """A valid-looking path subtype must not execute caller-defined route behavior."""
        _ExecutablePath.calls = 0
        self.assertIsNone(_mutation_route(_ExecutablePath("/v1/employment-records")))
        self.assertEqual(_ExecutablePath.calls, 0)

    def test_header_collection_subclass_is_rejected_before_iteration(self) -> None:
        """Header collection behavior must not run before exact container validation."""
        _ExecutableHeaders.calls = 0
        with self.assertRaises(_InvalidHttpRequest):
            _parse_command_headers({"headers": _ExecutableHeaders(_required_headers())})
        self.assertEqual(_ExecutableHeaders.calls, 0)

    def test_header_row_subclass_is_rejected_before_length(self) -> None:
        """Header row behavior must not run before exact pair validation."""
        _ExecutableHeaderRow.calls = 0
        headers = _required_headers()
        headers[0] = _ExecutableHeaderRow(headers[0])
        with self.assertRaises(_InvalidHttpRequest):
            _parse_command_headers({"headers": headers})
        self.assertEqual(_ExecutableHeaderRow.calls, 0)

    def test_header_bytes_subclass_is_rejected_before_lower(self) -> None:
        """Header scalar behavior must not run before exact bytes validation."""
        _ExecutableBytes.calls = 0
        headers = _required_headers()
        headers[0] = (_ExecutableBytes(b"idempotency-key"), headers[0][1])
        with self.assertRaises(_InvalidHttpRequest):
            _parse_command_headers({"headers": headers})
        self.assertEqual(_ExecutableBytes.calls, 0)

    def test_header_count_is_bounded(self) -> None:
        """More than 64 exact ASGI header pairs must fail before field parsing."""
        headers = _required_headers() + [(b"x-padding", b"a")] * 61
        with self.assertRaises(_InvalidHttpRequest):
            _parse_command_headers({"headers": headers})

    def test_individual_header_pair_is_bounded(self) -> None:
        """One exact pair beyond the byte ceiling must fail before decoding."""
        headers = _required_headers() + [(b"x-padding", b"a" * 16384)]
        with self.assertRaises(_InvalidHttpRequest):
            _parse_command_headers({"headers": headers})

    def test_aggregate_header_bytes_are_bounded(self) -> None:
        """Individually valid pairs must not bypass the total request-metadata budget."""
        headers = _required_headers() + [
            (b"x-padding-a", b"a" * 8200),
            (b"x-padding-b", b"b" * 8200),
        ]
        with self.assertRaises(_InvalidHttpRequest):
            _parse_command_headers({"headers": headers})


if __name__ == "__main__":
    unittest.main()
