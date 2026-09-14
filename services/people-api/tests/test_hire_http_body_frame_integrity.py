"""Adversarial ASGI body-frame authority contracts for confirmed hire."""

from __future__ import annotations

import unittest

from orgmetra_people_api.hire_http import _InvalidHttpRequest, _read_json_object


class _ExplodingFrame(dict[str, object]):
    """Expose frame method dispatch before exact-dict authority is proven."""

    def get(self, key: str, default: object = None) -> object:
        raise AssertionError("ASGI frame get executed before exact-dict rejection")


class _ExplodingStr(str):
    """Expose type comparison before exact-string authority is proven."""

    def __eq__(self, other: object) -> bool:
        raise AssertionError("ASGI message type equality executed before exact-string rejection")


class _ExplodingBytes(bytes):
    """Expose body sizing before exact-bytes authority is proven."""

    def __len__(self) -> int:
        raise AssertionError("ASGI body length executed before exact-bytes rejection")


class HireHttpBodyFrameIntegrityTests(unittest.IsolatedAsyncioTestCase):
    """Reject executable ASGI body-frame subtypes before structural operations."""

    async def test_frame_subclass_is_rejected_before_get(self) -> None:
        async def receive() -> dict[str, object]:
            return _ExplodingFrame({"type": "http.request", "body": b"{}", "more_body": False})

        with self.assertRaises(_InvalidHttpRequest):
            await _read_json_object(receive)

    async def test_message_type_subclass_is_rejected_before_equality(self) -> None:
        async def receive() -> dict[str, object]:
            return {"type": _ExplodingStr("http.request"), "body": b"{}", "more_body": False}

        with self.assertRaises(_InvalidHttpRequest):
            await _read_json_object(receive)

    async def test_body_subclass_is_rejected_before_length(self) -> None:
        async def receive() -> dict[str, object]:
            return {"type": "http.request", "body": _ExplodingBytes(b"{}"), "more_body": False}

        with self.assertRaises(_InvalidHttpRequest):
            await _read_json_object(receive)

    async def test_builtin_bytearray_is_not_an_asgi_body_scalar(self) -> None:
        async def receive() -> dict[str, object]:
            return {"type": "http.request", "body": bytearray(b"{}"), "more_body": False}

        with self.assertRaises(_InvalidHttpRequest):
            await _read_json_object(receive)

    async def test_exact_dict_string_and_bytes_frame_remains_supported(self) -> None:
        async def receive() -> dict[str, object]:
            return {"type": "http.request", "body": b"{}", "more_body": False}

        self.assertEqual(await _read_json_object(receive), {})


if __name__ == "__main__":
    unittest.main()
