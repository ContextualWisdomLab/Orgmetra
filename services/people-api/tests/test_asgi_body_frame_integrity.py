"""Regression contracts for bounded, inert ASGI request-body frames."""

from __future__ import annotations

import unittest

from orgmetra_people_api.hire_http import _InvalidHttpRequest, _read_json_object


class _ExplosiveFrame(dict[str, object]):
    """Prove frame validation happens before caller-defined mapping behavior."""

    def get(self, key: str, default: object = None) -> object:  # pragma: no cover - must never execute
        raise AssertionError(f"untrusted frame get executed for {key!r}")


class _ExplosiveText(str):
    """Prove the ASGI message type is reduced to an exact built-in scalar."""

    def __eq__(self, other: object) -> bool:  # pragma: no cover - must never execute
        raise AssertionError(f"untrusted message type equality executed for {other!r}")


class _BodyBytes(bytes):
    """Represent a behavior-capable bytes subtype that must not cross the body boundary."""


class AsgiBodyFrameIntegrityTests(unittest.IsolatedAsyncioTestCase):
    """Keep body framing inert before JSON parsing or governed persistence."""

    @staticmethod
    def _receiver(*frames: object):
        iterator = iter(frames)

        async def receive() -> object:
            return next(iterator)

        return receive

    async def test_behavior_bearing_frame_is_rejected_before_mapping_lookup(self) -> None:
        receive = self._receiver(
            _ExplosiveFrame(
                type="http.request",
                body=b"{}",
                more_body=False,
            )
        )
        with self.assertRaises(_InvalidHttpRequest):
            await _read_json_object(receive)  # type: ignore[arg-type]

    async def test_message_type_must_be_an_exact_string(self) -> None:
        receive = self._receiver(
            {
                "type": _ExplosiveText("http.request"),
                "body": b"{}",
                "more_body": False,
            }
        )
        with self.assertRaises(_InvalidHttpRequest):
            await _read_json_object(receive)  # type: ignore[arg-type]

    async def test_body_chunk_must_be_exact_immutable_bytes(self) -> None:
        for body in (bytearray(b"{}"), _BodyBytes(b"{}")):
            with self.subTest(body_type=type(body).__name__):
                receive = self._receiver(
                    {
                        "type": "http.request",
                        "body": body,
                        "more_body": False,
                    }
                )
                with self.assertRaises(_InvalidHttpRequest):
                    await _read_json_object(receive)  # type: ignore[arg-type]

    async def test_more_body_when_present_must_be_an_exact_bool(self) -> None:
        for more_body in (1, "false", None):
            with self.subTest(more_body=more_body):
                receive = self._receiver(
                    {
                        "type": "http.request",
                        "body": b"{}",
                        "more_body": more_body,
                    }
                )
                with self.assertRaises(_InvalidHttpRequest):
                    await _read_json_object(receive)  # type: ignore[arg-type]

    async def test_exact_multiframe_json_remains_supported(self) -> None:
        receive = self._receiver(
            {"type": "http.request", "body": b'{"allocation":', "more_body": True},
            {"type": "http.request", "body": b"1}", "more_body": False},
        )
        self.assertEqual(await _read_json_object(receive), {"allocation": 1})  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
